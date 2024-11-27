from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.quad_tree import QuadTree
from ers.structures.rect import Rect
from ers.util.serialization import ObjectToBytes
from extensions.schemes.hilbert.hilbert import Hilbert


class QuadBRCHilbert(Hilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.qtree = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        max_hilbert_index = 2 ** (self.dimension * self.edge_bits) - 1

        # Represent the search space as the elongated Hilbert curve line by setting y to 0
        self.qtree = QuadTree(
            Rect(Point(0, 0), Point(max_hilbert_index, 0)),
            self.edge_bits
        )

        modified_db = defaultdict(list)
        for index, files in tqdm(hilbert_plaintext_mm.items()):
            for rect_cover in self.qtree.find_containing_range_covers(Point(index, 0)):
                label_bytes = ObjectToBytes((rect_cover.start.x, rect_cover.end.x))
                modified_db[label_bytes].extend(files)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, p1: Point, p2: Point, false_positive_tolerance_factor: float = 0, downscale: bool = False) -> Set[bytes]:
        hilbert_ranges = self._hilbert_ranges(p1, p2, false_positive_tolerance_factor, downscale)

        trapdoors = set()

        for (start, end) in hilbert_ranges:
            for rect_cover in self.qtree.get_brc_range_cover(Rect(Point(start, 0), Point(end, 0))):
                label_bytes = ObjectToBytes((rect_cover.start.x, rect_cover.end.x))
                trapdoors.add(self.emm_engine.trapdoor(key, label_bytes))

        return trapdoors
