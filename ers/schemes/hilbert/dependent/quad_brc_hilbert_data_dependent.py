"""
Data-dependent Quad-BRC scheme over the Hilbert curve.

The ``2**d``-ary 1-D tree of :class:`~ers.schemes.hilbert.quad_brc_hilbert.QuadBRCHilbert`
cut by the mass of the projected curve distances. Once the cuts follow the
data, the nodes no longer coincide with the curve's quadrants, so this scheme
is *not* equivalent to its native counterpart. Best Range Cover; exact.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertBestRangeCover
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class QuadBRCHilbertDataDependent(HilbertBestRangeCover):
    """A Best-Range-Cover scheme over a mass-balanced 1-D ``2**d``-ary tree of Hilbert distances."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree([self.hilbert_bits], 2**self.dimensions, indexed_mm, weight=self.mass_weight)


class QuadBRCHilbertDataDependentRecords(QuadBRCHilbertDataDependent):
    """:class:`QuadBRCHilbertDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
