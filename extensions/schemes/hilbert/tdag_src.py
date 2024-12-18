from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.tdag import Tdag
from ers.util.serialization import ObjectToBytes
from extensions.schemes.hilbert.hilbert import Hilbert


class TdagSRCHilbert(Hilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tdag = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        max_hilbert_index = 2 ** (self.dimension * self.edge_bits) - 1

        tree_height = self.dimension * self.edge_bits
        self.tdag = Tdag.initialize_tree(tree_height)

        modified_db = defaultdict(list)
        for index, vals in tqdm(hilbert_plaintext_mm.items()):
            roots = _descend_tree(index, (0, max_hilbert_index))
            for label in roots:
                label_bytes = ObjectToBytes(label)
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, p1: Point, p2: Point, segment_gap_tolerance: float = 0, downscale_percentage: int = 0) -> Set[bytes]:
        trapdoors = set()
        hilbert_range = self._hilbert_range_src(p1, p2, downscale_percentage)
        cover = self.tdag.get_single_range_cover((hilbert_range[0], hilbert_range[1]))
        trapdoors.add(self.emm_engine.trapdoor(key, ObjectToBytes(cover)))
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
