from typing import Set, List, Dict

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.point import Point


class HilbertScheme(EMM):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine, dimensions)

        self.order = max(emm_engine.DIMENSIONS_BITS)
        self.hc = HilbertCurve(self.order, self.dimensions)

        self.encrypted_db = None

    def _hilbert_plaintext_mm(self, plaintext_mm: Dict[Point, List[bytes]]) -> Dict[int, List[bytes]]:
        for p in plaintext_mm.keys():
            assert p.dimensions() == self.dimensions

        return {self.hc.distance_from_point(p): plaintext_mm[p] for p in plaintext_mm.keys()}

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        results = set()

        if self.encrypted_db is None:
            return results

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results
