from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from .common.emm import EMM
from .common.emm_engine import EMMEngine
from ..structures.hyperrange import HyperRange
from ..structures.hyperrange_tree import HyperRangeTree
from ..structures.hyperrange_tree_product import HyperRangeTreeProduct
from ..structures.point import Point
from ..util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider


class TdagSRC(EMM):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tree_product = None
        self.encrypted_db = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        d1_trees = [HyperRangeTree.init(HyperRange.from_bits([h]), UniformSplitMidOverlapDivider(2)) for h in self.emm_engine.DIMENSIONS_BITS]
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

        rng = self.tree_product.src(query)
        assert rng is not None

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
