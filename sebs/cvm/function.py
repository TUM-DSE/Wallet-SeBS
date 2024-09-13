import concurrent.futures
import datetime
import sys
import time

import requests
from sebs.faas.function import ExecutionResult, Function, FunctionConfig, Trigger
from sebs.storage.config import MinioConfig


class HTTPTrigger(Trigger):
    def __init__(self, function):
        super().__init__()
        self.function = function

    @staticmethod
    def typename() -> str:
        return "Cvm.HTTPTrigger"

    @staticmethod
    def trigger_type() -> Trigger.TriggerType:
        return Trigger.TriggerType.HTTP

    def sync_invoke(self, payload: dict) -> ExecutionResult:
        self.logging.debug(f"Invoke function")
        cold: bool

        begin = datetime.datetime.now()

        if not self.function._running:
            cold = True

            sys.path.append("../../..")
            sys.path.append("../../../tasks")
            from tasks.vm import (
                VMResource,
                get_vm_resource,
                get_snp_direct_qemu_cmd,
            )
            from tasks.qemu import spawn_qemu
            from tasks.config import SSH_PORT

            vm: QemuVM
            resource: VMResource = get_vm_resource("snp", "small")
            config = {
                "image": "../../../build/image/guest-fs-sebs.qcow2",
                "ssh_port": SSH_PORT,
                "boot_prealloc": True,
            }
            qemu_cmd = get_snp_direct_qemu_cmd(resource, config)

            context = spawn_qemu(qemu_cmd, numa_node=resource.numa_node, config=config)
            self.function._context = context
            vm = context.__enter__()
            self.function._running = True

            vm.pin_vcpu(resource.pin_base)

            environment = {
                "CODE_LOCATION": self.function._code_location,
                "MINIO_ADDRESS": self.function._storage_cfg.address,
                "MINIO_ACCESS_KEY": self.function._storage_cfg.access_key,
                "MINIO_SECRET_KEY": self.function._storage_cfg.secret_key,
            }

            req = requests.post("http://localhost:9002/alive", environment)
            if req.status_code != 200:
                self.logging.error(req.text)

            self.logging.info(f"Started function")
        else:
            cold = False

        output = requests.post("http://localhost:9002", json=payload).json()
        end = datetime.datetime.now()

        result = ExecutionResult.from_times(begin, end)
        result.request_id = output["request_id"]
        result.parse_benchmark_output(output)
        result.stats.cold_start = cold
        return result

    def async_invoke(self, payload: dict) -> concurrent.futures.Future:
        pool = concurrent.futures.ThreadPoolExecutor()
        fut = pool.submit(self.sync_invoke, payload)
        return fut

    def serialize(self) -> dict:
        return {}

    @staticmethod
    def deserialize(obj: dict) -> Trigger:
        raise NotImplementedError()


class CvmFunction(Function):
    def __init__(
        self,
        name: str,
        benchmark: str,
        code_package_hash: str,
        code_location: str,
        config: FunctionConfig,
        storage_cfg: MinioConfig,
    ):
        super().__init__(benchmark, name, code_package_hash, config)
        self._code_location = code_location
        self._storage_cfg = storage_cfg

        self._running = False

        trigger = HTTPTrigger(self)
        super().add_trigger(trigger)

    @staticmethod
    def typename() -> str:
        return "Cvm.CvmFunction"

    def serialize(self) -> dict:
        return {
            **super().serialize(),
            "storage_cfg": self._storage_cfg.serialize(),
            "code_location": self._code_location,
        }

    @staticmethod
    def deserialize(cached_config: dict) -> "CvmFunction":
        return CvmFunction(
            cached_config["name"],
            cached_config["benchmark"],
            cached_config["hash"],
            cached_config["code_location"],
            FunctionConfig.deserialize(cached_config["config"]),
            MinioConfig.deserialize(cached_config["storage_cfg"]),
        )

    def add_trigger(self, trigger: Trigger):
        raise NotImplementedError()

    def stop(self):
        if self._running:
            self.logging.info(f"Stopping function")
            self._context.__exit__(None, None, None)
            self._running = False
            self.logging.info(f"Function stopped succesfully")
        else:
            self.logging.info("Not stopping function as it was not running")
