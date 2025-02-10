from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.point import Point
from ers.util.hyperrange.uniform_split_divider import UniformSplitDivider


class RangeBRCHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tree = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        tree_height = self.dimensions * self.order
        self.tree = HyperRangeTree.init(HyperRange.from_bits([tree_height]), UniformSplitDivider(2))

        modified_db = defaultdict(list)
        for distance, vals in tqdm(hilbert_plaintext_mm.items()):
            for rng in self.tree.descend(HyperRange.from_point_coords([distance])):
                label_bytes = rng.to_bytes()
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange, merging_tolerance: float = 0) -> Set[bytes]:
        ranges = self.hc.brc_with_merging(query, merging_tolerance)

        trapdoors = set()

        for (start_distance, end_distance) in ranges:
            for rng in self.tree.brc(HyperRange.from_coords([start_distance], [end_distance])):
                label_bytes = rng.to_bytes()
                trapdoors.add(self.emm_engine.trapdoor(key, label_bytes))

        return trapdoors