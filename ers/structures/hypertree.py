import functools
from typing import List, Tuple, Optional

from ers.structures.hyperrange import HyperRange
from ers.util.hyperrange.divider import HyperRangeDivider


class HyperTree:
    def __init__(
            self,
            children: List["HyperTree"],
            rng: HyperRange,
            height: int,
            division_strategy: HyperRangeDivider
    ):
        self.children = children
        self.rng = rng
        self.height = height
        self.division_strategy = division_strategy

    @classmethod
    def initialize_tree(
            cls,
            root: HyperRange,
            division_strategy: HyperRangeDivider
    ) -> "HyperTree":

        max_depth = -1

        def helper(depth: int, rng: HyperRange) -> HyperTree:
            nonlocal max_depth

            max_depth = max(max_depth, depth)
            children = division_strategy.divide(rng)

            assert len(children) > 0

            if len(children) == 1 and children[0] == rng:
                return cls([], rng, depth, division_strategy)
            else:
                return cls([helper(depth + 1, c) for c in children], rng, depth, division_strategy)

        def update_height(t: HyperTree):
            t.height = max_depth - t.height
            if len(t.children) == 0:
                assert t.rng.start == t.rng.end
            else:
                for c in t.children:
                    update_height(c)

            return t

        tree = update_height(helper(0, root))
        return tree

    def __str__(self):
        root_height = self.height

        def helper(t: HyperTree) -> str:
            s = "|    " * (root_height - t.height) + str(t.rng) + " - H: " + str(t.height) + "\n"
            for c in t.children:
                s += helper(c)
            return s

        return helper(self)

    def descend(self, rng: HyperRange) -> List[HyperRange]:
        if rng in self.rng:
            result = [self.rng]
            for c in self.children:
                result.extend(c.descend(rng))
            return result
        else:
            return []

    @functools.lru_cache(maxsize=None)
    def get_range_cover(self, query_range: HyperRange) -> List[Tuple[int, HyperRange]]:
        if self.rng in query_range:
            return [(self.height, self.rng)]
        else:
            result = []

            for child in self.children:
                child_res = child.get_range_cover(query_range)
                if child_res:
                    result.extend(child_res)

            return result

    @staticmethod
    def __remove_height_metadata(range_cover: List[Tuple[int, HyperRange]]):
        return [t[1] for t in range_cover]

    def get_src_range_cover(self, query_range: HyperRange) -> Optional[HyperRange]:
        if query_range in self.rng:
            for child in self.children:
                result = child.get_src_range_cover(query_range)
                if result is not None:
                    return result

            return self.rng
        else:
            return None

    def get_brc_range_cover(self, query_range: HyperRange) -> List[HyperRange]:
        range_cover = self.get_range_cover(query_range)
        return self.__remove_height_metadata(range_cover)

    def get_urc_range_cover(self, query_range: HyperRange) -> List[HyperRange]:
        range_cover = self.get_range_cover(query_range)
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