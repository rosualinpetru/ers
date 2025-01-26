from collections import defaultdict
from typing import Dict, List, Set

from tqdm import tqdm

from .common.emm import EMM
from .common.emm_engine import EMMEngine
from ..structures.hyperrange import HyperRange
from ..structures.hyperrange_tree import HyperRangeTree
from ..structures.point import Point
from ..util.hyperrange.uniform_split_divider import UniformSplitDivider


class ExpoSRC(EMM):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.tree = None
        self.encrypted_db = None

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        self.tree = HyperRangeTree.init(HyperRange.from_bits(self.emm_engine.DIMENSIONS_BITS), UniformSplitDivider(2))

        modified_db = defaultdict(list)
        for point, vals in tqdm(plaintext_mm.items()):
            assert point.dimensions() == self.dimensions

            for rng in self.tree.descend(point):
                label = rng.to_bytes()
                modified_db[label].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRange) -> Set[bytes]:
        trapdoors = set()

        rng = self.tree.src(query)
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
