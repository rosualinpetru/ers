from typing import List, Tuple, Optional

from ers.structures.hyperrange import HyperRange
from ers.util.hyperrange.divider import HyperRangeDivider


class HyperRangeTree:
    """
    Represents a hierarchical decomposition of a HyperRange using a division strategy.

    This class provides methods for constructing a tree of HyperRanges, searching for contained ranges,
    and performing range covering.
    """

    def __init__(self, children: List["HyperRangeTree"], rng: HyperRange, height: int, division_strategy: HyperRangeDivider):
        """
        Initializes a HyperRangeTree instance.

        :param children: List of child HyperRangeTree nodes.
        :param rng: The HyperRange represented by this node.
        :param height: The height of the tree from this node.
        :param division_strategy: The strategy used to divide the HyperRange.
        """
        self.children = children
        self.rng = rng
        self.height = height
        self.division_strategy = division_strategy
        self.dimensions = self.rng.dimensions
        for c in children:
            assert c.dimensions == self.dimensions

    @classmethod
    def init(cls, rng: HyperRange, division_strategy: HyperRangeDivider) -> "HyperRangeTree":
        """
        Constructs a HyperRangeTree using a division strategy.

        :param rng: The root HyperRange.
        :param division_strategy: The strategy to divide the HyperRange.
        :return: A HyperRangeTree instance.
        """
        children = division_strategy.divide(rng)

        if not children:
            return cls([], rng, 0, division_strategy)
        else:
            nodes = [HyperRangeTree.init(c, division_strategy) for c in children]
            max_children_height = max([c.height for c in nodes])
            return cls(nodes, rng, max_children_height + 1, division_strategy)

    def descend(self, rng: HyperRange) -> List[HyperRange]:
        """
        Recursively retrieves all ranges that contain the given range.

        :param rng: The HyperRange to search within.
        :return: A list of contained HyperRanges.
        """
        if rng in self.rng:
            result = [self.rng]
            for c in self.children:
                result.extend(c.descend(rng))
            return result
        else:
            return []

    def rc(self, rng: HyperRange) -> List[Tuple[int, HyperRange]]:
        """
        Retrieves all ranges contained within the given range, along with their heights.

        :param rng: The HyperRange to search within.
        :return: A list of tuples containing height and corresponding HyperRange.
        """
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
        """
        Finds the single range covering the given range.

        :param rng: The HyperRange to cover.
        :return: The single HyperRange covering the given range.
        """
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
        """
        Computes the best range covering (BRC) of the given range.

        :param rng: The HyperRange to cover.
        :return: A list of HyperRanges representing the BRC.
        """
        range_cover = self.rc(rng)
        return self.__remove_height_metadata(range_cover)

    def urc(self, rng: HyperRange) -> List[HyperRange]:
        """
        Computes the uniform range covering (URC) of the given range.

        :param rng: The HyperRange to cover.
        :return: A list of HyperRanges forming a uniform cover.
        """
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
        """
        Checks if the uniform region covering condition is met.

        :param range_cover: List of height-HyperRange tuples.
        :return: True if the URC condition is satisfied, False otherwise.
        """
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
        """
        Removes height metadata from the range cover tuples.

        :param range_cover: List of height-HyperRange tuples.
        :return: A list of HyperRanges.
        """
        return [t[1] for t in range_cover]

    def __str__(self):
        """
        Returns a string representation of the HyperRangeTree.

        :return: A formatted string representing the tree structure.
        """
        root_height = self.height

        def helper(t: HyperRangeTree) -> str:
            s = "|    " * (root_height - t.height) + str(t.rng) + " - H: " + str(t.height) + "\n"
            for c in t.children:
                s += helper(c)
            return s

        return helper(self)
