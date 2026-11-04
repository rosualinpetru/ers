"""
TDAG-SRC scheme (Falzon et al.).

The multi-dimensional TDAG: one uniform binary tree per dimension augmented
with mid-overlapping "cousin" nodes, taken as a product. Because a cousin
straddles every seam between two siblings, any query is contained in a single
product node, so queries use the Single Range Cover: exactly one token, at the
price of the false positives in the covering node.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree_product
from ers.schemes.common.structured_scheme import RangeSupportingStructure, SingleRangeCover
from ers.structures.point import Point


class TdagSRC(SingleRangeCover):
    """A Single-Range-Cover scheme over a product of per-dimension TDAGs."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree_product(self.emm_engine.DIMENSIONS_BITS, mid_overlap=True)
