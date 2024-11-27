from collections import defaultdict
from typing import Dict, List

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.rect import Rect
from ers.util.serialization import ObjectToBytes
from extensions.schemes.hilbert.hilbert import Hilbert
from extensions.structures.quad_tree_src import QuadTreeSRC


class QDagSRCHilbert(Hilbert):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.qdag = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_plaintext_mm = self._hilbert_plaintext_mm(plaintext_mm)

        max_hilbert_index = 2 ** (self.dimension * self.edge_bits) - 1

        qdag_height = self.dimension * self.edge_bits
        self.qdag = QuadTreeSRC(qdag_height, Rect(Point(0, 0), Point(max_hilbert_index, 0)), True)

        modified_db = defaultdict(list)
        for index, files in hilbert_plaintext_mm.items():
            for rect_cover in self.qdag.find_containing_range_covers(Point(index, 0)):
                label_bytes = ObjectToBytes((rect_cover.start.x, rect_cover.end.x))
                modified_db[label_bytes].extend(files)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, p1: Point, p2: Point, downscale: bool = False) -> bytes:
        hilbert_range = self._hilbert_ranges(p1, p2, self.emm_engine.MAX_X * self.emm_engine.MAX_Y, downscale)
        cover = self.qdag.get_single_range_cover(hilbert_range[0], hilbert_range[1])
        return self.emm_engine.trapdoor(key, ObjectToBytes(cover))
