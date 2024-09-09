import concurrent.futures

from sebs.faas.function import ExecutionResult, Function, FunctionConfig, Trigger


class HTTPTrigger(Trigger):
    def __init__(self, url: str):
        super().__init__()
        self.url = url

    @staticmethod
    def typename() -> str:
        return "Cvm.HTTPTrigger"

    @staticmethod
    def trigger_type() -> Trigger.TriggerType:
        return Trigger.TriggerType.HTTP

    def sync_invoke(self, payload: dict) -> ExecutionResult:
        self.logging.debug(f"Invoke function {self.url}")
        return self._http_invoke(payload, self.url)  # todo: misst die Zeit bei cold start nicht richtg

    def async_invoke(self, payload: dict) -> concurrent.futures.Future:
        pool = concurrent.futures.ThreadPoolExecutor()
        fut = pool.submit(self.sync_invoke, payload)
        return fut

    def serialize(self) -> dict:
        return {"type": "HTTP", "url": self.url}

    @staticmethod
    def deserialize(obj: dict) -> Trigger:
        return HTTPTrigger(obj["url"])


class CvmFunction(Function):
    def __init__(
        self,
        vm,
        context,
        port: int,
        name: str,
        benchmark: str,
        code_package_hash: str,
        config: FunctionConfig,
    ):
        super().__init__(benchmark, name, code_package_hash, config)
        self._instance = vm
        self._context = context
        self._port = port
        self._url = "{IPAddress}:{Port}".format(IPAddress="localhost", Port=port)

        trigger = HTTPTrigger("aaaaaaa")  # todo
        super().add_trigger(trigger)

    @property
    def url(self) -> str:
        return self._url

    @staticmethod
    def typename() -> str:
        return "Cvm.CvmFunction"

    def serialize(self) -> dict:
        raise NotImplementedError()
        return {}

    @staticmethod
    def deserialize(cached_config: dict) -> "CvmFunction":
        raise NotImplementedError()

    def add_trigger(self, trigger: Trigger):
        raise NotImplementedError()

    def stop(self):
        self.logging.info(f"Stopping function {self._instance_id}")
        self._context.__exit__(None, None, None)
        self.logging.info(f"Function {self._instance_id} stopped succesfully")
