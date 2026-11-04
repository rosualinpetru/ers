"""
Quad-SRC scheme (Falzon et al.).

The quadtree of :class:`~ers.schemes.quad_brc.QuadBRC` queried with the Single
Range Cover: one token for the smallest quad node containing the whole query.
Without cousin nodes a query straddling a cut is covered by the node above it,
up to the full domain, so precision can collapse; the TDAG family exists to
bound exactly that overshoot.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure, SingleRangeCover
from ers.structures.point import Point


class QuadSRC(SingleRangeCover):
    """A Single-Range-Cover scheme over a single quadtree-style range tree."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree(self.emm_engine.DIMENSIONS_BITS, 2)
