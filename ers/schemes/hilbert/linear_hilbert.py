from typing import Dict, List, Set

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.schemes.linear import Linear
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


class LinearHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine, dimensions)
        self.linear_scheme = Linear(emm_engine, 1)

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)
        self.linear_scheme.build_index(key, hilbert_plaintext_mm)
        self.encrypted_db = self.linear_scheme.encrypted_db

    def trapdoor(self, key: bytes, query: HyperRange, merging_tolerance: float = 0) -> Set[bytes]:
        assert query.dimensions == self.dimensions

        ranges = self.hc.best_range_cover_with_merging(query, merging_tolerance)

        trapdoors = set.union(
            *[self.linear_scheme.trapdoor(key, HyperRange.from_coords([start], [end])) for start, end in ranges]
        )

        return trapdoors
