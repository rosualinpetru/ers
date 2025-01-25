from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.structures.point import Point
from .common.emm import EMM
from .common.emm_engine import EMMEngine
from ..structures.hyperrange import HyperRange
from ..structures.hypertree_product import HyperTreeProduct
from ..util.hyperrange.uniform_split_divider import UniformSplitDivider


class RangeBRC(EMM):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tree_product = None
        self.encrypted_db = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        self.tree_product = HyperTreeProduct(self.emm_engine.DIMENSIONS_BITS, UniformSplitDivider(2))

        modified_db = defaultdict(list)
        for point, vals in tqdm(plaintext_mm.items()):
            assert point.dimensions() == self.dimensions

            for hyperrange in self.tree_product.parents_of(point):
                label = hyperrange.to_bytes()
                modified_db[label].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        trapdoors = set()

        for hyperrange in self.tree_product.generate_brc_cover(query):
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
