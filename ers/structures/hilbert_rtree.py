"""
Packed Hilbert R-tree (Kamel & Faloutsos, VLDB 1994).

Points are sorted by their Hilbert distance and chunked ``node_capacity`` at a
time into leaves; the shared :class:`PackedRTree` machinery packs the levels
above. Consecutive points on the curve are spatially close, so the leaves (and
their ancestors) get compact, low-overlap bounding boxes and a range query
descends few nodes -- the property that keeps the encrypted cover small.
"""

from typing import List

from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.packed_rtree import PackedRTree, RTreeNode
from ers.structures.point import Point

#: Kept for callers that imported the node type from this module.
HilbertRTreeNode = RTreeNode


class HilbertRTree(PackedRTree):
    """A bulk-loaded R-tree whose leaves are packed in Hilbert-curve order."""

    def __init__(self, root, hc: HilbertCurve, node_capacity: int):
        """
        :param root: The root node, or ``None`` for an empty tree.
        :param hc: The curve the points were sorted along.
        :param node_capacity: Maximum fan-out / leaf size.
        """
        super().__init__(root, node_capacity)
        self.hc = hc

    @classmethod
    def build(cls, points: List[Point], dimensions: int, order: int, node_capacity: int = 4) -> "HilbertRTree":
        """
        Bulk-loads a packed Hilbert R-tree over ``points``.

        :param points: The data points to index.
        :param dimensions: Number of spatial dimensions.
        :param order: Hilbert-curve order, used only to sort the points.
        :param node_capacity: Maximum fan-out / leaf size.
        :return: The tree.
        """
        hc = HilbertCurve(order, dimensions)
        ordered = sorted(points, key=hc.distance_from_point)
        chunks = [ordered[i : i + node_capacity] for i in range(0, len(ordered), node_capacity)]
        return cls(cls._pack(chunks, node_capacity), hc, node_capacity)
