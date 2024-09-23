import time

import concurrent.futures
import datetime
import os
import requests
import subprocess

from sebs.faas.function import ExecutionResult, Function, FunctionConfig, Trigger
from sebs.storage.config import MinioConfig


class HTTPTrigger(Trigger):
    def __init__(self, function):
        super().__init__()
        self.function = function

    @staticmethod
    def typename() -> str:
        return "KataFc.HTTPTrigger"

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
            environment_args = []
            for key, value in environment.items():
                environment_args.append("-e")
                environment_args.append(f"{key}='{value}'")

            self.function._container = subprocess.run(
                ["nerdctl", "run", "--rm", "-d", "--runtime", "io.containerd.kata-fc.v2", "--snapshotter", "devmapper",
                 *environment_args,                                     # environment variables
                 "-p", f"{self.function._port}:9003/tcp",               # port forwarding
                 "-v", f"{self.function._code_location}:/function:ro",  # volume mounts
                 "sebs:run.kata_qemu.python.3.11", "/bin/bash /sebs/run_server.sh 9003"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            ).stdout.strip()

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


class KataFcFunction(Function):
    def __init__(
            self,
            name: str,
            benchmark: str,
            code_package_hash: str,
            code_location: str,
            config: FunctionConfig,
            storage_cfg: MinioConfig,
            port: int
    ):
        super().__init__(benchmark, name, code_package_hash, config)
        self._code_location = code_location
        self._storage_cfg = storage_cfg
        self._port = port

        self._running = False

        trigger = HTTPTrigger(self)
        super().add_trigger(trigger)

    @staticmethod
    def typename() -> str:
        return "KataFc.KataFcFunction"

    def serialize(self) -> dict:
        return {
            **super().serialize(),
            "storage_cfg": self._storage_cfg.serialize(),
            "code_location": self._code_location,
            "port": self._port
        }

    @staticmethod
    def deserialize(cached_config: dict) -> "KataFcFunction":
        return KataFcFunction(
            cached_config["name"],
            cached_config["benchmark"],
            cached_config["hash"],
            cached_config["code_location"],
            FunctionConfig.deserialize(cached_config["config"]),
            MinioConfig.deserialize(cached_config["storage_cfg"]),
            cached_config["port"]
        )

    def add_trigger(self, trigger: Trigger):
        raise NotImplementedError()

    def stop(self):
        if self._running:
            self.logging.info(f"Stopping function")
            subprocess.run(
                ["nerdctl", "stop", self._container],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True
            )
            self._running = False
            self.logging.info(f"Function stopped succesfully")
        else:
            self.logging.info("Not stopping function as it was not running")
