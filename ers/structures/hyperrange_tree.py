from typing import List, Tuple, Optional

from ers.structures.hyperrange import HyperRange
from ers.util.hyperrange.divider import HyperRangeDivider


class HyperRangeTree:
    def __init__(self, children: List["HyperRangeTree"], rng: HyperRange, height: int, division_strategy: HyperRangeDivider):
        self.children = children
        self.rng = rng
        self.height = height
        self.division_strategy = division_strategy
        self.dimensions = self.rng.dimensions
        for c in children:
            assert c.dimensions == self.dimensions

    @classmethod
    def init(cls, rng: HyperRange, division_strategy: HyperRangeDivider) -> "HyperRangeTree":
        children = division_strategy.divide(rng)

        if not children:
            return cls([], rng, 0, division_strategy)
        else:
            nodes = [HyperRangeTree.init(c, division_strategy) for c in children]
            max_children_height = max([c.height for c in nodes])
            return cls([], rng, max_children_height + 1, division_strategy)


    def descend(self, rng: HyperRange) -> List[HyperRange]:
        if rng in self.rng:
            result = [self.rng]
            for c in self.children:
                result.extend(c.descend(rng))
            return result
        else:
            return []

    def rc(self, rng: HyperRange) -> List[Tuple[int, HyperRange]]:
        if self.rng in rng:
            return [(self.height, self.rng)]
        else:
            result = []

            for child in self.children:
                for res in child.rc(rng):
                    if res:
                        result.append(res)

            return result

    def src(self, rng: HyperRange) -> Optional[HyperRange]:
        if rng in self.rng:
            results = []
            for child in self.children:
                result = child.src(rng)
                if result is not None:
                    results.append(result)

            if results:
                return min(results, key=lambda r: r.volume())
            else:
                return self.rng
        else:
            return None

    def brc(self, rng: HyperRange) -> List[HyperRange]:
        range_cover = self.rc(rng)
        return self.__remove_height_metadata(range_cover)

    def urc(self, rng: HyperRange) -> List[HyperRange]:
        range_cover = self.rc(rng)
        while not self.__satisfies_urc_condition(range_cover):
            for r in reversed(range_cover):
                divisions = self.division_strategy.divide(r[1])
                if len(divisions) > 1:
                    split = [(r[0] - 1, d) for d in divisions]
                    range_cover.remove(r)
                    range_cover.extend(split)
                    break

        return self.__remove_height_metadata(range_cover)

    @staticmethod
    def __satisfies_urc_condition(range_cover: List[Tuple[int, HyperRange]]) -> bool:
        seen_levels = set()
        max_level = 0

        for result in range_cover:
            if result[0] > max_level:
                max_level = result[0]

            seen_levels.add(result[0])

        for lvl in range(0, max_level + 1):
            if lvl not in seen_levels:
                return False

        return True

    @staticmethod
    def __remove_height_metadata(range_cover: List[Tuple[int, HyperRange]]):
        return [t[1] for t in range_cover]

    def __str__(self):
        root_height = self.height

        def helper(t: HyperRangeTree) -> str:
            s = "|    " * (root_height - t.height) + str(t.rng) + " - H: " + str(t.height) + "\n"
            for c in t.children:
                s += helper(c)
            return s

        return helper(self)
