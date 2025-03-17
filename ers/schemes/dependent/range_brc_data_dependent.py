from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.hyperrange_tree_product import HyperRangeTreeProduct
from ers.structures.point import Point
from ers.util.hyperrange.data_dependent_split_divider import DataDependentSplitDivider


class RangeBRCDataDependent(EMM):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tree_product = None
        self.encrypted_db = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        d1_trees = [HyperRangeTree.init(HyperRange.from_bits([h]), DataDependentSplitDivider(2, plaintext_mm)) for h in self.emm_engine.DIMENSIONS_BITS]
        self.tree_product = HyperRangeTreeProduct(d1_trees)

        modified_db = defaultdict(list)
        for point, vals in tqdm(plaintext_mm.items()):
            assert point.dimensions() == self.dimensions

            for rng in self.tree_product.descend(point):
                label = rng.to_bytes()
                modified_db[label].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        trapdoors = set()

        for rng in self.tree_product.brc(query):
            label = rng.to_bytes()
            trapdoors.add(self.emm_engine.trapdoor(key, label))

        return trapdoors

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        results = set()

        if self.encrypted_db is None:
            raise ValueError("Index is not built yet!")

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results
