import docker
import os
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
            "python": ["storage.py", ".python_packages"],
        }
        package_config = CONFIG_FILES[language_name]
        function_dir = os.path.join(directory, "function")
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
        # todo
        raise NotImplementedError()

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
        raise NotImplementedError()

    def download_metrics(self, function_name: str, start_time: int, end_time: int, requests: Dict[str, ExecutionResult],
                         metrics: dict):
        pass

    def create_trigger(self, function: Function, trigger_type: Trigger.TriggerType) -> Trigger:
        # todo
        raise NotImplementedError()

    def shutdown(self) -> None:
        # todo
        raise NotImplementedError()
