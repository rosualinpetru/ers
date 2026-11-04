"""
Packed Hilbert R-tree scheme.

The range-supporting structure is a :class:`HilbertRTree`: points are packed
into bounded nodes in curve order, so covers are small and the index stores
each record once per tree level. This is the Hilbert curve used *for packing*
rather than for indexing: queries are answered on native bounding boxes.
"""

from typing import List

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.common.packed_rtree_scheme import PackedRTreeScheme
from ers.structures.hilbert_rtree import HilbertRTree
from ers.structures.packed_rtree import PackedRTree
from ers.structures.point import Point


class HilbertRTreeScheme(PackedRTreeScheme):
    """A range-search scheme over a packed Hilbert R-tree."""

    def __init__(self, emm_engine: EMMEngine, node_capacity: int = 4):
        """
        :param emm_engine: The engine providing the cryptographic primitives.
        :param node_capacity: Maximum R-tree fan-out / leaf size.
        """
        super().__init__(emm_engine, node_capacity)
        self.order = max(emm_engine.DIMENSIONS_BITS)

    def _build_tree(self, points: List[Point]) -> PackedRTree:
        return HilbertRTree.build(points, self.dimensions, self.order, self.node_capacity)
