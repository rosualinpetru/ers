from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert import HilbertScheme
from ers.structures.hyperrect import HyperRect
from ers.structures.pointnd import PointND
from ers.structures.tdag import Tdag


###################################################################################################
### GENERALISED
###################################################################################################

class TdagSRCHilbert(HilbertScheme):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine, dimensions)
        self.tdag = None

    def build_index(self, key: bytes, plaintext_mm: Dict[PointND, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        max_hilbert_index = 2 ** (self.dimensions * self.order) - 1

        tree_height = self.dimensions * self.order
        self.tdag = Tdag.initialize_tree(tree_height)

        modified_db = defaultdict(list)
        for index, vals in tqdm(hilbert_plaintext_mm.items()):
            roots = _descend_tree(index, (0, max_hilbert_index))
            for label in roots:
                label_bytes = HyperRect.from_coords([label[0]], [label[1]]).to_bytes()
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRect) -> Set[bytes]:
        trapdoors = set()
        hilbert_range = self.hc.single_range_cover(query)
        cover = self.tdag.get_single_range_cover(hilbert_range)
        label_bytes = HyperRect.from_coords([cover[0]], [cover[1]]).to_bytes()
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


###################################################################################################
### CONCRETE
###################################################################################################

class TdagSRCHilbert2D(TdagSRCHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 2)


class TdagSRCHilbert3D(TdagSRCHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 3)
