from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.point_3d import Point3D
from ers.structures.tdag import Tdag
from ers.util.serialization import ObjectToBytes
from extensions.schemes.hilbert.hilbert import Hilbert
from extensions.structures.hyperrect import HyperRect
from extensions.structures.range import Range
from extensions.structures.pointnd import PointND


###################################################################################################
### GENERALISED
###################################################################################################

class TdagSRCHilbert(Hilbert):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine, dimensions)
        self.tdag = None

    def _build_index(self, key: bytes, plaintext_mm: Dict[PointND, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        max_hilbert_index = 2 ** (self.dimensions * self.edge_bits) - 1

        tree_height = self.dimensions * self.edge_bits
        self.tdag = Tdag.initialize_tree(tree_height)

        modified_db = defaultdict(list)
        for index, vals in tqdm(hilbert_plaintext_mm.items()):
            roots = _descend_tree(index, (0, max_hilbert_index))
            for label in roots:
                label_bytes = Range(label[0], label[1]).to_bytes()
                modified_db[label_bytes].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def _trapdoor(self, key: bytes, query: HyperRect, segment_gap_tolerance: float = 0, downscale_percentage: int = 0) -> Set[bytes]:
        trapdoors = set()
        hilbert_range = self._hilbert_range_src(query, downscale_percentage)
        cover = self.tdag.get_single_range_cover((hilbert_range.start, hilbert_range.end))
        trapdoors.add(self.emm_engine.trapdoor(key, Range(cover[0], cover[1]).to_bytes()))
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
### IMPLEMENTATIONS
###################################################################################################

class TdagSRCHilbert2D(TdagSRCHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 2)

    def _build_index(self, key: bytes, plaintext_mm: Dict[PointND, List[bytes]]):
        super()._build_index(key, {PointND([p.x, p.y]): plaintext_mm[p] for p in plaintext_mm.keys()})

    def trapdoor(self, key: bytes, p1: PointND, p2: PointND, segment_gap_tolerance: float = 0, downscale_bits: int = 0) -> Set[bytes]:
        return super()._trapdoor(key, HyperRect(PointND([p1.x, p1.y]), PointND([p2.x, p2.y])), segment_gap_tolerance, downscale_bits)


class TdagSRCHilbert3D(TdagSRCHilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 3)

    def build_index(self, key: bytes, plaintext_mm: Dict[Point3D, List[bytes]]):
        super()._build_index(key, {PointND([p.x, p.y, p.z]): plaintext_mm[p] for p in plaintext_mm.keys()})

    def trapdoor(self, key: bytes, p1: Point3D, p2: Point3D, segment_gap_tolerance: float = 0, downscale_bits: int = 0) -> Set[bytes]:
        return super()._trapdoor(key, HyperRect(PointND([p1.x, p1.y, p1.z]), PointND([p2.x, p2.y, p2.z])), segment_gap_tolerance, downscale_bits)
