from collections import defaultdict
from typing import Dict, List, Set

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hyperrect import HyperRect
from ers.structures.pointnd import PointND


###################################################################################################
### GENERALISED
###################################################################################################

class Linear(EMM):
    def __init__(self, emm_engine: EMMEngine, dimensions: int):
        super().__init__(emm_engine)
        self.dimensions = dimensions
        self.encrypted_db = None

    def build_index(self, key: bytes, plaintext_mm: Dict[PointND, List[bytes]]):
        modified_db = defaultdict(list)

        for point, vals in plaintext_mm.items():
            assert len(point.coords) == self.dimensions
            label = HyperRect(point, point).to_bytes()
            modified_db[label].extend(vals)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, query: HyperRect) -> Set[bytes]:
        trapdoors = set()

        for point in query.points():
            label = HyperRect(point, point).to_bytes()
            trapdoors.add(self.emm_engine.trapdoor(key, label))

        return trapdoors

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        results = set()

        if self.encrypted_db is None:
            raise ValueError("Index is not built yet!")

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results


###################################################################################################
### CONCRETE
###################################################################################################

class Linear2D(Linear):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 2)


class Linear3D(Linear):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine, 3)
