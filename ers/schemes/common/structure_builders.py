"""
Constructors for the range-supporting structures the schemes index with.

Every tree-based scheme is "a structure plus a cover rule". The structures come
in two shapes:

* a **single tree** over the whole (possibly multi-dimensional) domain, split
  with a given fan-out per dimension -- a binary tree in 1-D, a quadtree in 2-D,
  an octree in 3-D; and
* a **product of per-dimension trees** -- the multi-dimensional range tree of
  Falzon et al., where each dimension has its own 1-D tree and a node of the
  product is a tuple of per-dimension nodes.

Each shape has a *uniform* divider (cut by length), a *data-dependent* divider
(cut by point mass), and a *mid-overlap* flag that inserts the overlapping
"cousin" nodes turning a range tree into a TDAG (the structure that guarantees
a Single Range Cover).
"""

from typing import Dict, List

from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree import HyperRangeTree
from ers.structures.hyperrange_tree_product import HyperRangeTreeProduct
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight
from ers.util.hyperrange.data_dependent_split_divider import DataDependentSplitDivider
from ers.util.hyperrange.data_dependent_split_mid_overlap_divider import DataDependentSplitMidOverlapDivider
from ers.util.hyperrange.divider import HyperRangeDivider
from ers.util.hyperrange.uniform_split_divider import UniformSplitDivider
from ers.util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider


def uniform_tree(bits: List[int], fanout: int, mid_overlap: bool = False) -> HyperRangeTree:
    """
    A single tree over the domain ``[0, 2**bits[i])`` per dimension, cutting
    every dimension into ``fanout`` equal chunks per level.

    :param bits: Bit length of each dimension of the domain.
    :param fanout: Chunks per dimension per level (2 gives a binary / quad / oct tree).
    :param mid_overlap: Insert the TDAG cousin nodes straddling each seam.
    :return: The root of the tree.
    """
    divider: HyperRangeDivider = UniformSplitMidOverlapDivider(fanout) if mid_overlap else UniformSplitDivider(fanout)
    return HyperRangeTree.init(HyperRange.from_bits(bits), divider)


def data_dependent_tree(
    bits: List[int], fanout: int, plaintext_mm: Dict[Point, List[bytes]], mid_overlap: bool = False, weight: MassWeight = "cells"
) -> HyperRangeTree:
    """
    A single tree over the domain whose cuts follow the empirical mass of
    ``plaintext_mm`` instead of the domain length.

    :param bits: Bit length of each dimension of the domain.
    :param fanout: Mass-balanced chunks per dimension per level.
    :param plaintext_mm: The multi-map whose distribution places the cuts.
    :param mid_overlap: Insert mass-centred TDAG cousin nodes straddling each seam.
    :param weight: ``"cells"`` balances occupied cells (the benchmarked setting), ``"records"`` balances records.
    :return: The root of the tree.
    """
    divider: HyperRangeDivider = (
        DataDependentSplitMidOverlapDivider(fanout, plaintext_mm, weight) if mid_overlap else DataDependentSplitDivider(fanout, plaintext_mm, weight)
    )
    return HyperRangeTree.init(HyperRange.from_bits(bits), divider)


def uniform_tree_product(bits: List[int], mid_overlap: bool = False) -> HyperRangeTreeProduct:
    """
    The product of one uniform binary tree per dimension (a multi-dimensional
    range tree, or a multi-dimensional TDAG with ``mid_overlap``).

    :param bits: Bit length of each dimension; one tree is built per entry.
    :param mid_overlap: Insert the TDAG cousin nodes in every per-dimension tree.
    :return: The product structure.
    """
    return HyperRangeTreeProduct([uniform_tree([h], 2, mid_overlap) for h in bits])


def data_dependent_tree_product(
    bits: List[int], plaintext_mm: Dict[Point, List[bytes]], mid_overlap: bool = False, weight: MassWeight = "cells"
) -> HyperRangeTreeProduct:
    """
    The product of one mass-balanced binary tree per dimension.

    Each per-dimension tree receives the multi-map *projected onto its own
    axis*, so it adapts to that axis's marginal distribution. (Handing every
    tree the full multi-dimensional multi-map would make all of them adapt to
    the marginal of dimension 0.) Records of points sharing a coordinate are
    merged, so ``weight="records"`` balances records per axis value.

    :param bits: Bit length of each dimension; one tree is built per entry.
    :param plaintext_mm: The multi-map whose per-axis marginals place the cuts.
    :param mid_overlap: Insert mass-centred TDAG cousin nodes in every tree.
    :param weight: ``"cells"`` balances occupied cells (the benchmarked setting), ``"records"`` balances records.
    :return: The product structure.
    """
    trees = []
    for dim, h in enumerate(bits):
        projected_mm: Dict[Point, List[bytes]] = {}
        for p, vals in plaintext_mm.items():
            projected_mm.setdefault(Point([p[dim]]), []).extend(vals)
        trees.append(data_dependent_tree([h], 2, projected_mm, mid_overlap, weight))
    return HyperRangeTreeProduct(trees)
