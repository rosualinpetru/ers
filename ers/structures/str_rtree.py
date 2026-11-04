"""
STR-packed (Sort-Tile-Recursive) R-tree (Leutenegger et al., ICDE 1997) -- the
*native* packed R-tree, with no space-filling curve involved.

STR packing for ``n`` points, ``d`` dimensions and leaf capacity ``c``:

1. Compute the number of leaves ``P = ceil(n / c)``.
2. Sort the points by their first coordinate and cut them into
   ``S = ceil(P**(1/d))`` *slabs* of (nearly) equal size.
3. Recurse inside each slab on the remaining ``d - 1`` dimensions; at the last
   dimension, sort and chunk directly into leaves of ``c`` points.
4. Pack the leaves, which come out in a tile-like spatial order, level by
   level (shared :class:`PackedRTree` machinery).

The result is a balanced tree of low-overlap axis-aligned tiles -- exactly the
shape axis-aligned range queries probe.
"""

import math
from typing import List

from ers.structures.packed_rtree import PackedRTree, RTreeNode
from ers.structures.point import Point

__all__ = ["STRRTree", "RTreeNode"]


class STRRTree(PackedRTree):
    """A bulk-loaded R-tree whose leaves are packed by Sort-Tile-Recursive tiling."""

    @classmethod
    def build(cls, points: List[Point], dimensions: int, node_capacity: int = 4) -> "STRRTree":
        """
        Bulk-loads an STR-packed R-tree over ``points``.

        :param points: The data points to index.
        :param dimensions: Number of spatial dimensions.
        :param node_capacity: Maximum fan-out / leaf size.
        :return: The tree.
        """
        chunks = cls._str_tiles(points, 0, dimensions, node_capacity) if points else []
        return cls(cls._pack(chunks, node_capacity), node_capacity)

    @classmethod
    def _str_tiles(cls, points: List[Point], dim: int, dimensions: int, capacity: int) -> List[List[Point]]:
        """
        Recursively tiles ``points`` into leaf-sized chunks, slab by slab.

        :param points: The points to tile.
        :param dim: The dimension this level of the recursion slices along.
        :param dimensions: Total number of dimensions.
        :param capacity: Leaf capacity.
        :return: Leaf chunks in tile order, each holding at most ``capacity`` points.
        """
        if len(points) <= capacity:
            return [points]

        ordered = sorted(points, key=lambda p: p[dim])

        # Last dimension: chunk the sorted run directly into leaves.
        if dim == dimensions - 1:
            return [ordered[i : i + capacity] for i in range(0, len(ordered), capacity)]

        # Cut into S slabs so that, after recursing through the remaining
        # dimensions, roughly P = n/c leaves come out as a d-dimensional tiling.
        leaves_needed = math.ceil(len(ordered) / capacity)
        slabs = math.ceil(leaves_needed ** (1 / (dimensions - dim)))
        slab_size = math.ceil(len(ordered) / slabs)

        tiles: List[List[Point]] = []
        for i in range(0, len(ordered), slab_size):
            tiles.extend(cls._str_tiles(ordered[i : i + slab_size], dim + 1, dimensions, capacity))
        return tiles
