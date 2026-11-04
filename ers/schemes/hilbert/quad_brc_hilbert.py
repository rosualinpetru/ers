"""
Quad-BRC scheme over the Hilbert curve.

A single 1-D tree over the Hilbert domain with fan-out ``2**d`` per level. Its
nodes coincide with the quadrants of the curve's recursive construction, so
with uniform splits this scheme builds *the same index* as the native
:class:`~ers.schemes.quad_brc.QuadBRC` (only the node representation differs:
a curve interval instead of a bounding box). Queries use the Best Range Cover
of every Hilbert segment and are exact at merging tolerance 0.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertBestRangeCover
from ers.structures.point import Point


class QuadBRCHilbert(HilbertBestRangeCover):
    """A Best-Range-Cover scheme over a 1-D ``2**d``-ary tree of Hilbert distances."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree([self.hilbert_bits], 2**self.dimensions)
