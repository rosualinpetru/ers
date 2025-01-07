from .emm_engine import EMMEngine

from typing import Set


class EMM:
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        self.emm_engine = emm_engine
        self.dimensions = dimensions

        if self.emm_engine.dimensions != dimensions:
            raise ValueError("Engine is not configured correctly for the required number of dimensions")

    def setup(self, security_parameter: int) -> bytes:
        return self.emm_engine.setup(security_parameter)

    def resolve(self, key: bytes, results: Set[bytes]) -> Set[bytes]:
        return self.emm_engine.resolve(key, results)
