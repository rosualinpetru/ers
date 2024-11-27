from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.range_tree import RangeTree
from ers.util.serialization import ObjectToBytes
from extensions.schemes.hilbert.hilbert import Hilbert


class RangeBRCHilbert(Hilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tree = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        max_hilbert_index = 2 ** (self.dimension * self.edge_bits) - 1

        tree_height = self.dimension * self.edge_bits
        self.tree = RangeTree.initialize_tree(tree_height)

        modified_db = defaultdict(list)
        for index, vals in tqdm(hilbert_plaintext_mm.items()):
            roots = _descend_tree(index, (0, max_hilbert_index))
            for label in roots:
                label_bytes = ObjectToBytes(label)
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, p1: Point, p2: Point, false_positive_tolerance_factor: float = 0, downscale: bool = False) -> Set[bytes]:
        hilbert_ranges = self._hilbert_ranges(p1, p2, false_positive_tolerance_factor, downscale)

        trapdoors = set()

        for r in hilbert_ranges:
            for label in self.tree.get_brc_range_cover(r):
                label_bytes = ObjectToBytes(label)
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
