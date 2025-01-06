from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.structures.point_3d import Point3D
from ers.structures.range_tree import RangeTree
from ers.structures.hyperrect import HyperRect
from ers.structures.pointnd import PointND


###################################################################################################
### GENERALISED
###################################################################################################

class RangeBRCHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine, dimensions):
        super().__init__(emm_engine, dimensions)
        self.tree = None

    def build_index(self, key: bytes, plaintext_mm: Dict[PointND, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        max_hilbert_index = 2 ** (self.dimensions * self.order) - 1

        tree_height = self.dimensions * self.order
        self.tree = RangeTree.initialize_tree(tree_height)

        modified_db = defaultdict(list)
        for index, vals in tqdm(hilbert_plaintext_mm.items()):
            roots = _descend_tree(index, (0, max_hilbert_index))
            for label in roots:
                label_bytes = HyperRect.from_coords([label[0]], [label[1]]).to_bytes()
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def _trapdoor(self, key: bytes, query: HyperRect, merging_tolerance: float = 0) -> Set[bytes]:
        ranges = self.hc.best_range_cover_with_merging(query, merging_tolerance)

        trapdoors = set()

        for r in ranges:
            for label in self.tree.get_brc_range_cover(r):
                label_bytes = HyperRect.from_coords([label[0]], [label[1]]).to_bytes()
                trapdoors.add(self.emm_engine.trapdoor(key, label_bytes))

        return trapdoors


def _descend_tree(val: int, r: tuple[int, int]) -> List[tuple[int, int]]:
    ranges = []
    while r != (val, val):
        ranges.append(r)
        if val <= ((r[0] + r[1]) // 2):
            r = (r[0], ((r[0] + r[1]) // 2))
        else:
            r = (((r[0] + r[1]) // 2) + 1, r[1])

    ranges.append((val, val))
    return ranges


###################################################################################################
### CONCRETE
###################################################################################################

class RangeBRCHilbert2D(RangeBRCHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 2)


class RangeBRCHilbert3D(RangeBRCHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 3)
