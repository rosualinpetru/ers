from typing import Dict, List, Set

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.schemes.linear import Linear
from ers.structures.hyperrect import HyperRect
from ers.structures.pointnd import PointND


###################################################################################################
### GENERALISED
###################################################################################################

class LinearHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine, dimensions)
        self.linear_scheme = Linear(emm_engine, 1)

    def build_index(self, key: bytes, plaintext_mm: Dict[PointND, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)
        self.linear_scheme.build_index(key, hilbert_plaintext_mm)
        self.encrypted_db = self.linear_scheme.encrypted_db

    def trapdoor(self, key: bytes, query: HyperRect, merging_tolerance: float = 0) -> Set[bytes]:
        ranges = self.hc.best_range_cover_with_merging(query, merging_tolerance)

        trapdoors = set.union(
            *[self.linear_scheme.trapdoor(key, HyperRect.from_coords([start], [end])) for start, end in ranges]
        )

        return trapdoors


###################################################################################################
### CONCRETE
###################################################################################################

class LinearHilbert2D(LinearHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 2)


class LinearHilbert3D(LinearHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 3)
