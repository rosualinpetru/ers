from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.point import Point
from ers.util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider


class TdagSRCHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tdag = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        tdag_height = self.dimensions * self.order
        self.tdag = HyperRangeTree.init(HyperRange.from_bits([tdag_height]), UniformSplitMidOverlapDivider(2))

        modified_db = defaultdict(list)
        for distance, vals in tqdm(hilbert_plaintext_mm.items()):
            for rng in self.tdag.descend(HyperRange.from_point_coords([distance])):
                label_bytes = rng.to_bytes()
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        trapdoors = set()
        hilbert_range = self.hc.src(query)

        rng = self.tdag.src(HyperRange.from_coords([hilbert_range[0]], [hilbert_range[1]]))
        assert rng is not None

        label_bytes = rng.to_bytes()
        trapdoors.add(self.emm_engine.trapdoor(key, label_bytes))

        return trapdoors