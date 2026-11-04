"""
TDAG-SRC scheme over the Hilbert curve.

A single uniform TDAG (binary tree plus mid-overlap cousins) over the 1-D
Hilbert domain, queried with the Single Range Cover of the ``[min, max]`` curve
interval of the query. One token per query; the curve's excursions outside the
rectangle between those two extremes come back as false positives.

Scale note: the TDAG is built over the *entire* ``2**(d*n)`` Hilbert domain,
so this scheme is only practical for domains up to roughly ``2**14`` cells.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import uniform_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertSingleRangeCover
from ers.structures.point import Point


class TdagSRCHilbert(HilbertSingleRangeCover):
    """A Single-Range-Cover scheme over a 1-D TDAG of Hilbert distances."""

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return uniform_tree([self.hilbert_bits], 2, mid_overlap=True)
