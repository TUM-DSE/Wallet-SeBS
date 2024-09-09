import sys

import docker
import os
from pathlib import Path
import shutil
from typing import Dict, List, Tuple, Type, Optional, cast

from sebs.benchmark import Benchmark
from sebs.cache import Cache
from sebs.config import SeBSConfig
from sebs.cvm.config import CvmConfig
from sebs.cvm.function import CvmFunction
from sebs.cvm.storage import Minio
from sebs.faas import PersistentStorage
from sebs.faas.function import Function, Trigger, ExecutionResult
from sebs.faas.system import System
from sebs.utils import LoggingHandlers


class Cvm(System):
    PORT = 9001

    @staticmethod
    def name() -> str:
        return "cvm"

    def __init__(
        self,
        system_config: SeBSConfig,
        config: CvmConfig,
        cache_client: Cache,
        docker_client: docker.client,
        logger_handlers: LoggingHandlers,
    ):
        super().__init__(system_config, cache_client, docker_client)
        self._config = config
        self.logging_handlers = logger_handlers
        self._functions = []

    def initialize(self, config: Dict[str, str] = {}, resource_prefix: Optional[str] = None):
        self.initialize_resources(select_prefix="cvm")

    @property
    def config(self) -> CvmConfig:
        return self._config

    @staticmethod
    def function_type() -> "Type[Function]":
        return CvmFunction

    def get_storage(self, replace_existing: bool = False) -> PersistentStorage:
        if not hasattr(self, "storage"):
            if not self.config.resources.storage_config:
                raise RuntimeError(
                    "The CVM deployment is missing the configuration of pre-allocated storage!"
                )
            self.storage = Minio.deserialize(
                self.config.resources.storage_config, self.cache_client, self.config.resources
            )
            self.storage.logging_handlers = self.logging_handlers
        else:
            self.storage.replace_existing = replace_existing
        return self.storage

    def package_code(self, directory: str, language_name: str, language_version: str, benchmark: str,
                     is_cached: bool) -> Tuple[str, int]:
        CONFIG_FILES = {
            "python": [],
        }
        package_config = CONFIG_FILES[language_name]
        function_dir = Path(directory).parent.parent.parent.joinpath("function")
        os.makedirs(function_dir)
        # move all files to 'function' except handler.py
        for file in os.listdir(directory):
            if file not in package_config:
                file = os.path.join(directory, file)
                shutil.move(file, function_dir)

        bytes_size = os.path.getsize(directory)
        mbytes = bytes_size / 1024.0 / 1024.0
        self.logging.info("Function size {:2f} MB".format(mbytes))

        return directory, bytes_size

    def create_function(self, code_package: Benchmark, func_name: str) -> Function:
        sys.path.append("../../..")
        sys.path.append("../../../tasks")
        from tasks.vm import (
            VMResource,
            get_vm_resource,
            get_snp_direct_qemu_cmd,
            get_amd_vm_direct_qemu_cmd,
        )
        from tasks.qemu import spawn_qemu
        from tasks.config import SSH_PORT

        vm: QemuVM
        resource: VMResource = get_vm_resource("snp", "small")
        config = {
            "image": "../../../build/image/guest-fs-sebs.qcow2",
            "ssh_port": SSH_PORT,
            "boot_prealloc": True,  # todo
        }

        qemu_cmd = get_snp_direct_qemu_cmd(resource, config)
        qemu_cmd = get_amd_vm_direct_qemu_cmd(resource, config)  # todo: type snp
        context = spawn_qemu(qemu_cmd, numa_node=resource.numa_node, config=config)

        self._functions.append(context)
        vm = context.__enter__()
        vm.pin_vcpu(resource.pin_base)

        # todo
        vm.wait_for_ssh()

        # todo
        # from invoke import MockContext
        # c = MockContext()
        # vm.start(c, type="amd", size="small", image="../CVM_eval/build/image/guest-fs-serverless-bench-python.qcow2", action="ssh-cmd", ssh_cmd=["ls /"])

        raise NotImplementedError()

        environment = {
            "MINIO_ADDRESS": self.config.resources.storage_config.address,
            "MINIO_ACCESS_KEY": self.config.resources.storage_config.access_key,
            "MINIO_SECRET_KEY": self.config.resources.storage_config.secret_key,
        }

        func = CvmFunction(  # todo: store context here
            vm,
            self.PORT,
            func_name,
            code_package.benchmark,
            code_package.hash,
            function_cfg,
            pid,
        )
        self._functions.append(func)

        # Wait until server starts
        max_attempts = 10
        attempts = 0
        while attempts < max_attempts:
            try:
                requests.get(f"http://{func.url}/alive")
                break
            except requests.exceptions.ConnectionError:
                time.sleep(0.25)
                attempts += 1

        if attempts == max_attempts:
            raise RuntimeError(
                f"Couldn't start {func_name} function at container "
                f"{container.id} , running on {func._url}"
            )

        self.logging.info(
            f"Started {func_name} function at container {container.id} , running on {func._url}"
        )

        return func

    def cached_function(self, function: Function):
        raise NotImplementedError()

    def update_function(self, function: Function, code_package: Benchmark):
        raise NotImplementedError()

    def update_function_configuration(self, cached_function: Function, benchmark: Benchmark):
        raise NotImplementedError()

    def is_configuration_changed(self, cached_function: Function, benchmark: Benchmark) -> bool:
        changed = super().is_configuration_changed(cached_function, benchmark)

        storage = cast(Minio, self.get_storage())
        function = cast(CvmFunction, cached_function)
        # check if now we're using a new storage
        if function.config.storage != storage.config:
            self.logging.info(
                "Updating function configuration due to changed storage configuration."
            )
            changed = True
            function.config.storage = storage.config

        return changed

    def default_function_name(self, code_package: Benchmark) -> str:
        return f"{code_package.benchmark}-{code_package.language_name}-{code_package.language_version}"

    def enforce_cold_start(self, functions: List[Function], code_package: Benchmark):
        # todo
        for function in functions:
            function = cast(CvmFunction, function)
            function.stop()

    def download_metrics(self, function_name: str, start_time: int, end_time: int, requests: Dict[str, ExecutionResult],
                         metrics: dict):
        pass

    def create_trigger(self, function: Function, trigger_type: Trigger.TriggerType) -> Trigger:
        raise NotImplementedError()

    def shutdown(self) -> None:
        for function in self._functions:
            function.stop()
