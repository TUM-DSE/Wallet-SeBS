import os
import shutil
from typing import Dict, List, Tuple, Type, Optional, cast

import docker
from sebs.benchmark import Benchmark
from sebs.cache import Cache
from sebs.config import SeBSConfig
from sebs.gramine.config import GramineConfig
from sebs.gramine.function import GramineFunction
from sebs.gramine.storage import Minio
from sebs.faas import PersistentStorage
from sebs.faas.function import Function, Trigger, ExecutionResult, FunctionConfig
from sebs.faas.system import System
from sebs.utils import LoggingHandlers


class Gramine(System):
    @staticmethod
    def name() -> str:
        return "gramine"

    def __init__(
        self,
        system_config: SeBSConfig,
        config: GramineConfig,
        cache_client: Cache,
        docker_client: docker.client,
        logger_handlers: LoggingHandlers,
    ):
        super().__init__(system_config, cache_client, docker_client)
        self._config = config
        self.logging_handlers = logger_handlers
        self._functions = []
        self._port = 9004

    def initialize(
        self, config: Dict[str, str] = {}, resource_prefix: Optional[str] = None
    ):
        self.initialize_resources(select_prefix="gramine-docker")

    @property
    def config(self) -> GramineConfig:
        return self._config

    @staticmethod
    def function_type() -> "Type[Function]":
        return GramineFunction

    def get_storage(self, replace_existing: bool = False) -> PersistentStorage:
        if not hasattr(self, "storage"):
            if not self.config.resources.storage_config:
                raise RuntimeError(
                    "The gramine deployment is missing the configuration of pre-allocated storage!"
                )
            self.storage = Minio.deserialize(
                self.config.resources.storage_config,
                self.cache_client,
                self.config.resources,
            )
            self.storage.logging_handlers = self.logging_handlers
        else:
            self.storage.replace_existing = replace_existing
        return self.storage

    def package_code(
        self,
        directory: str,
        language_name: str,
        language_version: str,
        benchmark: str,
        is_cached: bool,
    ) -> Tuple[str, int]:
        CONFIG_FILES = {
            "python": ["handler.py", "requirements.txt", ".python_packages"],
            "nodejs": ["handler.js", "package.json", "node_modules"],
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
        function_cfg = FunctionConfig.from_benchmark(code_package)
        func = GramineFunction(
            func_name,
            code_package.benchmark,
            code_package.hash,
            code_package.code_location,
            function_cfg,
            self.config.resources.storage_config,
            self._docker_client,
            self._port,
        )
        func.logging_handlers = self.logging_handlers
        self._functions.append(func)
        self._port += 1
        return func

    def cached_function(self, function: Function):
        pass

    def update_function(self, function: Function, code_package: Benchmark):
        raise NotImplementedError()

    def update_function_configuration(
        self, cached_function: Function, benchmark: Benchmark
    ):
        raise NotImplementedError()

    def is_configuration_changed(
        self, cached_function: Function, benchmark: Benchmark
    ) -> bool:
        changed = super().is_configuration_changed(cached_function, benchmark)

        storage = cast(Minio, self.get_storage())
        function = cast(GramineFunction, cached_function)
        # check if now we're using a new storage
        if function._storage_cfg != storage.config:
            self.logging.info(
                "Updating function configuration due to changed storage configuration."
            )
            changed = True
            function._storage_cfg = storage.config

        return changed

    def default_function_name(self, code_package: Benchmark) -> str:
        return f"{code_package.benchmark}-{code_package.language_name}-{code_package.language_version}"

    def enforce_cold_start(self, functions: List[Function], code_package: Benchmark):
        for function in functions:
            function = cast(GramineFunction, function)
            function.stop()

    def download_metrics(
        self,
        function_name: str,
        start_time: int,
        end_time: int,
        requests: Dict[str, ExecutionResult],
        metrics: dict,
    ):
        pass

    def create_trigger(
        self, function: Function, trigger_type: Trigger.TriggerType
    ) -> Trigger:
        raise NotImplementedError()

    def shutdown(self) -> None:
        for function in self._functions:
            function.stop()
