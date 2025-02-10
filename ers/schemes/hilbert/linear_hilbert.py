from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point


class LinearHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        modified_db = defaultdict(list)

        for distance, vals in tqdm(hilbert_plaintext_mm.items()):
            label = HyperRange.from_point_coords([distance]).to_bytes()
            modified_db[label].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange, merging_tolerance: float = 0) -> Set[bytes]:
        assert query.dimensions == self.dimensions

        ranges = self.hc.brc_with_merging(query, merging_tolerance)

        trapdoors = set()

        for (start_distance, end_distance) in ranges:
            for distance in range(start_distance, end_distance + 1):
                label = HyperRange.from_point_coords([distance]).to_bytes()
                trapdoors.add(self.emm_engine.trapdoor(key, label))

        return trapdoors
