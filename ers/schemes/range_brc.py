from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.structures.point import Point
from .common.emm import EMM
from .common.emm_engine import EMMEngine
from ..structures.hyperrange import HyperRange
from ..structures.range_tree_md import RangeTreeMD


class RangeBRC(EMM):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine, dimensions)
        self.range_tree_md = None
        self.encrypted_db = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        self.range_tree_md = RangeTreeMD(self.emm_engine.DIMENSIONS_BITS)

        modified_db = defaultdict(list)
        for point, vals in tqdm(plaintext_mm.items()):
            assert point.dimensions() == self.dimensions

            for hyperrange in self.range_tree_md.parents_of(point):
                label = hyperrange.to_bytes()
                modified_db[label].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        trapdoors = set()

        for hyperrange in self.range_tree_md.generate_cover(query):
            label = hyperrange.to_bytes()
            trapdoors.add(self.emm_engine.trapdoor(key, label))

        return trapdoors

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        results = set()

        if self.encrypted_db is None:
            raise ValueError("Index is not built yet!")

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results
