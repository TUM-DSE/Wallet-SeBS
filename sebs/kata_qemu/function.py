import time

import concurrent.futures
import datetime
import docker
import os
import requests

from sebs.faas.function import ExecutionResult, Function, FunctionConfig, Trigger
from sebs.storage.config import MinioConfig


class HTTPTrigger(Trigger):
    def __init__(self, function):
        super().__init__()
        self.function = function

    @staticmethod
    def typename() -> str:
        return "KataQemu.HTTPTrigger"

    @staticmethod
    def trigger_type() -> Trigger.TriggerType:
        return Trigger.TriggerType.HTTP

    def sync_invoke(self, payload: dict) -> ExecutionResult:
        self.logging.debug(f"Invoke function")
        cold: bool

        begin = datetime.datetime.now()

        if not self.function._running:
            cold = True

            environment = {
                "MINIO_ADDRESS": self.function._storage_cfg.address,
                "MINIO_ACCESS_KEY": self.function._storage_cfg.access_key,
                "MINIO_SECRET_KEY": self.function._storage_cfg.secret_key,
                "CONTAINER_UID": str(os.getuid()),
                "CONTAINER_GID": str(os.getgid()),
                "CONTAINER_USER": "docker_user",
            }
            self.function._container = self.function._docker_client.containers.run(
                runtime="kata-qemu",
                image="sebs:run.kata_qemu.python.3.11",  # make name parametric
                command=f"/bin/bash /sebs/run_server.sh 9003",
                volumes={self.function._code_location: {"bind": "/function", "mode": "ro"}},
                environment=environment,
                mem_limit="1g",
                # network_mode="",
                ports={'9003/tcp': self.function._port},
                remove=True,
                stdout=True,
                stderr=True,
                detach=True,
            )
            self.function._running = True

            self._url = "{IPAddress}:{Port}".format(
                IPAddress="localhost",
                Port=self.function._port)

            # Wait until server starts
            max_attempts = 1000
            attempts = 0
            req = None
            while attempts < max_attempts:
                try:
                    req = requests.get(f"http://{self._url}/alive")
                    break
                except requests.exceptions.ConnectionError:
                    time.sleep(0.001)
                    attempts += 1

            if attempts == max_attempts:
                raise RuntimeError("Couldn't start function container")

            if req.status_code != 200:
                raise RuntimeError(req.text)

            self.logging.info(f"Started function")
        else:
            cold = False

        output = requests.post(f"http://{self._url}", json=payload).json()
        end = datetime.datetime.now()

        result = ExecutionResult.from_times(begin, end)
        result.request_id = output["request_id"]
        result.parse_benchmark_output(output)
        result.times.http_startup = 0
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


class KataQemuFunction(Function):
    def __init__(
            self,
            name: str,
            benchmark: str,
            code_package_hash: str,
            code_location: str,
            config: FunctionConfig,
            storage_cfg: MinioConfig,
            docker_client: docker.client,
            port: int
    ):
        super().__init__(benchmark, name, code_package_hash, config)
        self._code_location = code_location
        self._storage_cfg = storage_cfg
        self._docker_client = docker_client
        self._port = port

        self._running = False

        trigger = HTTPTrigger(self)
        super().add_trigger(trigger)

    @staticmethod
    def typename() -> str:
        return "KataQemu.KataQemuFunction"

    def serialize(self) -> dict:
        return {
            **super().serialize(),
            "storage_cfg": self._storage_cfg.serialize(),
            "code_location": self._code_location,
            "port": self._port
        }

    @staticmethod
    def deserialize(cached_config: dict) -> "KataQemuFunction":
        return KataQemuFunction(
            cached_config["name"],
            cached_config["benchmark"],
            cached_config["hash"],
            cached_config["code_location"],
            FunctionConfig.deserialize(cached_config["config"]),
            MinioConfig.deserialize(cached_config["storage_cfg"]),
            docker.from_env(),
            cached_config["port"]
        )

    def add_trigger(self, trigger: Trigger):
        raise NotImplementedError()

    def stop(self):
        if self._running:
            self.logging.info(f"Stopping function")
            self._container.remove(force=True)
            self._running = False
            self.logging.info(f"Function stopped succesfully")
        else:
            self.logging.info("Not stopping function as it was not running")
