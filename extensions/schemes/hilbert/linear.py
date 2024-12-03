from collections import defaultdict
from typing import Dict, List, Set

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.util.serialization import ObjectToBytes
from extensions.schemes.hilbert.hilbert import Hilbert


class LinearHilbert(Hilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        modified_db = defaultdict(list)
        for index, vals in hilbert_plaintext_mm.items():
            modified_db[ObjectToBytes(index)].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, p1: Point, p2: Point, segment_gap_tolerance: float = 0, downscale_percentage: int = 0) -> Set[bytes]:
        hilbert_ranges = self._hilbert_ranges(p1, p2, segment_gap_tolerance, downscale_percentage)

        trapdoors = set()

        for (start, end) in hilbert_ranges:
            for index in range(start, end + 1):
                label_bytes = ObjectToBytes(index)
                trapdoors.add(self.emm_engine.trapdoor(key, label_bytes))

        return trapdoors
