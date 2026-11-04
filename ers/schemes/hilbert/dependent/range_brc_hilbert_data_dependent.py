"""
Data-dependent Range-BRC scheme over the Hilbert curve.

The 1-D binary tree of :class:`~ers.schemes.hilbert.range_brc_hilbert.RangeBRCHilbert`
cut by the mass of the projected curve distances instead of by length. Best
Range Cover of every Hilbert segment; exact at merging tolerance 0.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertBestRangeCover
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class RangeBRCHilbertDataDependent(HilbertBestRangeCover):
    """A Best-Range-Cover scheme over a mass-balanced 1-D binary tree of Hilbert distances."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree([self.hilbert_bits], 2, indexed_mm, weight=self.mass_weight)


class RangeBRCHilbertDataDependentRecords(RangeBRCHilbertDataDependent):
    """:class:`RangeBRCHilbertDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
