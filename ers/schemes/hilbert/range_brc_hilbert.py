"""
Range-BRC scheme over the Hilbert curve.

A single uniform binary tree over the 1-D Hilbert domain, queried with the
Best Range Cover of every Hilbert segment of the query. Exact at merging
tolerance 0. Unlike the native range tree product, it only indexes ranges that
are *contiguous on the curve*, which is why its index is smaller and its covers
are larger than :class:`~ers.schemes.range_brc.RangeBRC`'s.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertBestRangeCover
from ers.structures.point import Point


class RangeBRCHilbert(HilbertBestRangeCover):
    """A Best-Range-Cover scheme over a 1-D binary tree of Hilbert distances."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree([self.hilbert_bits], 2)
