import math
from typing import Set, List, Dict

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.pointnd import PointND


class HilbertScheme(EMM):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine)

        self.order = math.ceil(math.log2(max(emm_engine.MAX_VALS)))
        self.dimensions = dimensions
        self.hc = HilbertCurve(self.order, self.dimensions)

        self.encrypted_db = None

    def _hilbert_plaintext_mm(self, plaintext_mm: Dict[PointND, List[bytes]]):
        return {PointND([self.hc.distance_from_point(p)]): plaintext_mm[p] for p in plaintext_mm.keys()}

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        results = set()

        if self.encrypted_db is None:
            return results

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results
