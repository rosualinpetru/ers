##
## Copyright 2024 Alin-Petru Rosu and Evangelia Anna Markatou
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##

import math
from collections import defaultdict
from typing import Dict, List, Set

from hilbertcurve.hilbertcurve import HilbertCurve

from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.rect import Rect
from extensions.schemes.hilbert.interval_division import IntervalDivision


class Linear1D(EMM):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.encrypted_db = None

    def build_index(self, key: bytes, plaintext_mm: Dict[int, List[bytes]]):
        modified_db = defaultdict(list)
        for point, files in plaintext_mm.items():
            modified_db[bytes(point)].extend(files)

        self.encrypted_db = self.emm_engine.build_index(key, modified_db)

    def trapdoor(self, key: bytes, lower: int, upper: int) -> Set[bytes]:
        trapdoors = set()

        for point in range(lower, upper + 1):
            trapdoors.add(self.emm_engine.trapdoor(key, bytes(point)))

        return trapdoors

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        results = set()

        if self.encrypted_db is None:
            return results

        for trapdoor in trapdoors:
            results = results.union(self.emm_engine.search(trapdoor, self.encrypted_db))

        return results


class Hilbert(EMM):
    def __init__(self, emm_engine: EMMEngine):
        super().__init__(emm_engine)
        self.encrypted_db = None

        self.__linear = Linear1D(emm_engine)

        self.iterations = math.ceil(math.log2(max(emm_engine.MAX_X, emm_engine.MAX_Y)))
        self.hc = HilbertCurve(self.iterations, 2)

    def build_index(self, key: bytes, plaintext_mm: Dict[Point, List[bytes]]):
        hilbert_index_dict = {self.hc.distance_from_point([pt.x, pt.y]): plaintext_mm[pt] for pt in plaintext_mm.keys()}
        self.__linear.build_index(key, hilbert_index_dict)
        self.encrypted_db = self.__linear.encrypted_db

    def trapdoor(self, key: bytes, rect: Rect, interval_division: IntervalDivision) -> Set[bytes]:
        trapdoors = set()

        for r in interval_division.divide(self.hc, rect):
            trapdoors = trapdoors.union(self.__linear.trapdoor(key, r[0], r[1]))

        return trapdoors

    def search(self, trapdoors: Set[bytes]) -> Set[bytes]:
        if self.encrypted_db is None:
            return set()

        return self.__linear.search(trapdoors)


