"""
Native STR-packed R-tree scheme.

The counterpart of :class:`~ers.schemes.hilbert.hilbert_rtree_scheme.HilbertRTreeScheme`
with the curve removed: leaves are packed by Sort-Tile-Recursive axis tiling.
Everything else (labelling, indexing, covering) is shared, so benchmarking the
two side by side isolates what the Hilbert packing order contributes.
"""

from typing import List

from ers.schemes.common.packed_rtree_scheme import PackedRTreeScheme
from ers.structures.packed_rtree import PackedRTree
from ers.structures.point import Point
from ers.structures.str_rtree import STRRTree


class RTreeScheme(PackedRTreeScheme):
    """A range-search scheme over an STR-packed R-tree."""

    def _build_tree(self, points: List[Point]) -> PackedRTree:
        return STRRTree.build(points, self.dimensions, self.node_capacity)
