"""
Quad-BRC scheme (Falzon et al.).

A single tree over the whole domain that halves every dimension at each level
(a quadtree in 2-D, an octree in 3-D). Queries use the Best Range Cover and
are exact. Compared with the range tree product, the index is much smaller
(each point lies in one node per level instead of a product of nodes) and the
covers are larger.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree
from ers.schemes.common.structured_scheme import BestRangeCover, RangeSupportingStructure
from ers.structures.point import Point


class QuadBRC(BestRangeCover):
    """A Best-Range-Cover scheme over a single quadtree-style range tree."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree(self.emm_engine.DIMENSIONS_BITS, 2)
