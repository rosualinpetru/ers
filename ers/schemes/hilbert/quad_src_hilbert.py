"""
Quad-SRC scheme over the Hilbert curve.

The ``2**d``-ary Hilbert tree of :class:`~ers.schemes.hilbert.quad_brc_hilbert.QuadBRCHilbert`
queried with the Single Range Cover of the ``[min, max]`` curve interval of the
query: one token, and the same index as the native
:class:`~ers.schemes.quad_src.QuadSRC`.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertSingleRangeCover
from ers.structures.point import Point


class QuadSRCHilbert(HilbertSingleRangeCover):
    """A Single-Range-Cover scheme over a 1-D ``2**d``-ary tree of Hilbert distances."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree([self.hilbert_bits], 2**self.dimensions)
