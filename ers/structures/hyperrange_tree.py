"""
Range-supporting trees: a hierarchical decomposition of a HyperRange by a divider.

A :class:`HyperRangeTree` is the generic range-supporting data structure of
Falzon et al.: every node is a canonical range, the root is the whole domain,
and children are produced by a :class:`HyperRangeDivider` (uniform or
data-dependent cuts, with or without TDAG mid-overlap cousins). The tree offers
the three cover rules (``brc``, ``src``, ``urc``) and ``descend`` for indexing.
"""

from typing import Dict, List, Optional, Tuple

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
    def init(cls, rng: HyperRange, division_strategy: HyperRangeDivider, _shared: Optional[Dict[HyperRange, "HyperRangeTree"]] = None) -> "HyperRangeTree":
        """
        Constructs the range-supporting DAG rooted at ``rng``.

        Identical canonical ranges are built **once** and shared: when a
        divider yields a range that already exists elsewhere (as the TDAG
        mid-overlap dividers do -- a cousin's halves are the halves of its
        two neighbours), the existing node is reused instead of growing a
        duplicate subtree. This turns the "tree" into the directed acyclic
        graph of Falzon et al. and keeps the node count linear in the domain;
        a naive tree duplicates every cousin subtree and both the structure
        and the index entries derived from it blow up exponentially in the
        depth.

        :param rng: The root HyperRange.
        :param division_strategy: The strategy to divide the HyperRange.
        :param _shared: Internal: the range -> node registry shared across the recursion.
        :return: The root node.
        """
        shared: Dict[HyperRange, "HyperRangeTree"] = {} if _shared is None else _shared
        if rng in shared:
            return shared[rng]

        children = division_strategy.divide(rng)
        if not children:
            node = cls([], rng, 0, division_strategy)
        else:
            nodes = [HyperRangeTree.init(c, division_strategy, shared) for c in children]
            node = cls(nodes, rng, max(c.height for c in nodes) + 1, division_strategy)
        shared[rng] = node
        return node

    def nodes(self) -> List["HyperRangeTree"]:
        """Every distinct node reachable from this one, in depth-first order."""
        seen = set()
        result = []
        stack: List["HyperRangeTree"] = [self]
        while stack:
            n = stack.pop()
            if n.rng in seen:
                continue
            seen.add(n.rng)
            result.append(n)
            stack.extend(reversed(n.children))
        return result

    def descend(self, rng: HyperRange) -> List[HyperRange]:
        """
        Retrieves every distinct canonical range that contains the given range
        (the root-to-leaf path in a tree; all such nodes in a DAG).

        :param rng: The HyperRange to locate (typically a single point).
        :return: The containing canonical ranges, each exactly once.
        """
        if rng not in self.rng:
            return []
        seen = set()
        result = []
        stack: List["HyperRangeTree"] = [self]
        while stack:
            n = stack.pop()
            if n.rng in seen or rng not in n.rng:
                continue
            seen.add(n.rng)
            result.append(n.rng)
            stack.extend(reversed(n.children))
        return result

    def rc(self, rng: HyperRange) -> List[Tuple[int, HyperRange]]:
        """
        The maximal canonical ranges contained in ``rng`` (the range cover),
        each exactly once, with their heights.

        Only vertices intersecting ``rng`` are expanded: a vertex disjoint from
        the query cannot have a descendant inside it, so the traversal costs
        ``O(|cover| * height)`` instead of visiting the whole structure.

        :param rng: The HyperRange to cover.
        :return: A list of ``(height, canonical range)`` tuples.
        """
        seen = set()
        result = []
        stack: List["HyperRangeTree"] = [self]
        while stack:
            n = stack.pop()
            if n.rng in seen or not n.rng.intersects(rng):
                continue
            seen.add(n.rng)
            if n.rng in rng:
                result.append((n.height, n.rng))
            else:
                stack.extend(reversed(n.children))
        return result

    def src(self, rng: HyperRange) -> Optional[HyperRange]:
        """
        Finds the single smallest canonical range containing the given range.

        :param rng: The HyperRange to cover.
        :return: The smallest containing canonical range, or ``None`` if the
            root does not contain ``rng``.
        """
        if rng not in self.rng:
            return None
        best = self.rng
        seen = set()
        stack: List["HyperRangeTree"] = [self]
        while stack:
            n = stack.pop()
            if n.rng in seen:
                continue
            seen.add(n.rng)
            if rng in n.rng:
                if n.rng.volume() < best.volume():
                    best = n.rng
                stack.extend(n.children)
        return best

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
            # Shared (DAG) nodes are printed under every parent, as a tree view.
            s = "|    " * (root_height - t.height) + str(t.rng) + " - H: " + str(t.height) + "\n"
            for c in t.children:
                s += helper(c)
            return s

        return helper(self)
