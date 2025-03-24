from typing import cast, Optional

from sebs.cache import Cache
from sebs.faas.config import Config, Credentials, Resources
from sebs.storage.minio import MinioConfig
from sebs.utils import LoggingHandlers


class WalletWarmCredentials(Credentials):
    def serialize(self) -> dict:
        return {}

    @staticmethod
    def deserialize(
        config: dict, cache: Cache, handlers: LoggingHandlers
    ) -> Credentials:
        return WalletCredentials()


"""
    No need to cache and store - we prepare the benchmark and finish.
    The rest is used later by the user.
"""


class WalletWarmResources(Resources):
    def __init__(self, storage_cfg: Optional[MinioConfig] = None):
        super().__init__(name="wallet_warm")
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
        ret = WalletWarmResources()
        # Check for new config
        if "storage" in config:
            ret._storage = MinioConfig.deserialize(config["storage"])
            ret.logging.info(
                "Using user-provided configuration of storage for wallet_warm."
            )
        return ret


class WalletWarmConfig(Config):
    def __init__(self):
        super().__init__(name="wallet_warm")
        self._credentials = WalletWarmCredentials()
        self._resources = WalletWarmResources()

    @staticmethod
    def typename() -> str:
        return "WalletWarm.Config"

    @staticmethod
    def initialize(cfg: Config, dct: dict):
        pass

    @property
    def credentials(self) -> WalletWarmCredentials:
        return self._credentials

    @property
    def resources(self) -> WalletWarmResources:
        return self._resources

    @resources.setter
    def resources(self, val: WalletWarmResources):
        self._resources = val

    @staticmethod
    def deserialize(config: dict, cache: Cache, handlers: LoggingHandlers) -> Config:
        config_obj = WalletWarmConfig()
        config_obj.resources = cast(
            WalletWarmResources, WalletWarmResources.deserialize(config, cache, handlers)
        )
        config_obj.logging_handlers = handlers
        return config_obj

    def serialize(self) -> dict:
        return {"name": "wallet_warm"}

    def update_cache(self, cache: Cache):
        pass
