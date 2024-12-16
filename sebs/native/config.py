from typing import cast, Optional

from sebs.cache import Cache
from sebs.faas.config import Config, Credentials, Resources
from sebs.storage.minio import MinioConfig
from sebs.utils import LoggingHandlers


class NativeCredentials(Credentials):
    def serialize(self) -> dict:
        return {}

    @staticmethod
    def deserialize(
            config: dict, cache: Cache, handlers: LoggingHandlers
    ) -> Credentials:
        return NativeCredentials()


"""
    No need to cache and store - we prepare the benchmark and finish.
    The rest is used later by the user.
"""


class NativeResources(Resources):
    def __init__(self, storage_cfg: Optional[MinioConfig] = None):
        super().__init__(name="native")
        self._storage = storage_cfg

    @property
    def storage_config(self) -> Optional[MinioConfig]:
        return self._storage

    def serialize(self) -> dict:
        return {}

    @staticmethod
    def initialize(res: Resources, cfg: dict):
        pass

    @staticmethod
    def deserialize(config: dict, cache: Cache, handlers: LoggingHandlers) -> Resources:
        ret = NativeResources()
        # Check for new config
        if "storage" in config:
            ret._storage = MinioConfig.deserialize(config["storage"])
            ret.logging.info(
                "Using user-provided configuration of storage for native."
            )
        return ret


class NativeConfig(Config):
    def __init__(self):
        super().__init__(name="native")
        self._credentials = NativeCredentials()
        self._resources = NativeResources()

    @staticmethod
    def typename() -> str:
        return "Native.Config"

    @staticmethod
    def initialize(cfg: Config, dct: dict):
        pass

    @property
    def credentials(self) -> NativeCredentials:
        return self._credentials

    @property
    def resources(self) -> NativeResources:
        return self._resources

    @resources.setter
    def resources(self, val: NativeResources):
        self._resources = val

    @staticmethod
    def deserialize(config: dict, cache: Cache, handlers: LoggingHandlers) -> Config:
        config_obj = NativeConfig()
        config_obj.resources = cast(
            NativeResources, NativeResources.deserialize(config, cache, handlers)
        )
        config_obj.logging_handlers = handlers
        return config_obj

    def serialize(self) -> dict:
        return {"name": "native"}

    def update_cache(self, cache: Cache):
        pass
