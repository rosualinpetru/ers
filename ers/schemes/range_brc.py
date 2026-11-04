"""
Range-BRC scheme (Falzon et al.).

The multi-dimensional range tree: one uniform binary tree per dimension, taken
as a product, so every point is indexed under the product of the per-dimension
nodes covering it. Queries use the Best Range Cover and are exact.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree_product
from ers.schemes.common.structured_scheme import BestRangeCover, RangeSupportingStructure
from ers.structures.point import Point


class RangeBRC(BestRangeCover):
    """A Best-Range-Cover scheme over a product of per-dimension binary range trees."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree_product(self.emm_engine.DIMENSIONS_BITS)
