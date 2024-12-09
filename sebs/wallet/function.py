import time
import concurrent.futures
import datetime
import requests
import os
import subprocess

from sebs.faas.function import ExecutionResult, Function, FunctionConfig, Trigger
from sebs.storage.config import MinioConfig


class HTTPTrigger(Trigger):
    def __init__(self, function):
        super().__init__()
        self.function = function

    @staticmethod
    def typename() -> str:
        return "Wallet.HTTPTrigger"

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
                "CODE_LOCATION": self.function._code_location,
                "MINIO_ADDRESS": self.function._storage_cfg.address,
                "MINIO_ACCESS_KEY": self.function._storage_cfg.access_key,
                "MINIO_SECRET_KEY": self.function._storage_cfg.secret_key,
                "TRUSTLET": self.function._trustlet
            }

            self.logging.info(f"starting server for trustlet number: {self.function._trustlet}")

            self.function._context = subprocess.Popen([
                'python-venv/bin/python',
                f'{self.function._code_location}/server.py' if os.path.exists(f'{self.function._code_location}/server.py') else 'dockerfiles/wallet/python/server.py',
                '9002'
            ], env=environment)
            self.function._running = True

            # Wait until server starts
            max_attempts = 1100
            attempts = 0
            req = None
            while attempts < max_attempts:
                try:
                    req = requests.get("http://localhost:9002/alive")
                    break
                except requests.exceptions.ConnectionError:
                    time.sleep(0.01)
                    attempts += 1

            if attempts == max_attempts:
                raise RuntimeError("Couldn't start function")

            if req.status_code != 200:
                raise RuntimeError(req.text)

            self.logging.info(f"Started function")
        else:
            cold = False

        output = requests.post("http://localhost:9002", json=payload)
        if output.status_code != 200:
            self.function.stop()
            raise RuntimeError(f"Couldn't invoke function; output:\n{output.text}")
        output = output.json()
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


class WalletFunction(Function):
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
        return "Wallet.WalletFunction"

    def serialize(self) -> dict:
        return {
            **super().serialize(),
            "storage_cfg": self._storage_cfg.serialize(),
            "code_location": self._code_location,
            "trustlet": self._trustlet,
        }

    @staticmethod
    def deserialize(cached_config: dict) -> "WalletFunction":
        function = WalletFunction(
            cached_config["name"],
            cached_config["benchmark"],
            cached_config["hash"],
            cached_config["code_location"],
            FunctionConfig.deserialize(cached_config["config"]),
            MinioConfig.deserialize(cached_config["storage_cfg"]),
        )
        function._trustlet = cached_config["trustlet"]
        return function

    def add_trigger(self, trigger: Trigger):
        raise NotImplementedError()

    def stop(self):
        if self._running:
            self.logging.info(f"Stopping function")
            self._context.kill()
            self._running = False
            self.logging.info(f"Function stopped succesfully")
        else:
            self.logging.info("Not stopping function as it was not running")
