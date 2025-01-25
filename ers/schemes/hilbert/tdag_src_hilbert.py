from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.structures.hyperrange import HyperRange
from ers.structures.hypertree import HyperTree
from ers.structures.point import Point
from ers.util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider


class TdagSRCHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tdag = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        tdag_height = self.dimensions * self.order
        self.tdag = HyperTree.initialize_tree(HyperRange.from_coords([0], [pow(2, tdag_height) - 1]), UniformSplitMidOverlapDivider(2))

        modified_db = defaultdict(list)
        for distance, vals in tqdm(hilbert_plaintext_mm.items()):
            for hyperrange in self.tdag.descend(HyperRange(Point([distance]), Point([distance]))):
                label_bytes = hyperrange.to_bytes()
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        trapdoors = set()
        hilbert_range = self.hc.single_range_cover(query)
        hyperrange = HyperRange.from_coords([hilbert_range[0]], [hilbert_range[1]])
        cover = self.tdag.get_src_range_cover(hyperrange)
        assert cover is not None
        label_bytes = cover.to_bytes()
        trapdoors.add(self.emm_engine.trapdoor(key, label_bytes))
        return trapdoors


def _descend_tree(val: int, r: tuple[int, int]) -> List[tuple[int, int]]:
    ranges = []
    while r != (val, val):
        if r not in ranges:
            ranges.append(r)

        middle = ((r[0] + r[1]) // 2)

        mid_0 = (middle - ((r[0] + r[1]) // 4))
        mid_1 = (middle + ((r[0] + r[1]) // 4)) + 1

        if mid_0 <= val <= mid_1 and (r[1] - r[0]) > 1:
            if (mid_0, mid_1) not in ranges:
                ranges.append((mid_0, mid_1))

        if val <= ((r[0] + r[1]) // 2):
            r = (r[0], ((r[0] + r[1]) // 2))
        else:
            r = (((r[0] + r[1]) // 2) + 1, r[1])

    ranges.append((val, val))
    return ranges
