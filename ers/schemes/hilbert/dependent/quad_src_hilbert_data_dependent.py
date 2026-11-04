"""
Data-dependent Quad-SRC scheme over the Hilbert curve.

The mass-balanced ``2**d``-ary 1-D tree queried with the Single Range Cover of
the ``[min, max]`` curve interval of the query: one token per query.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertSingleRangeCover
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class QuadSRCHilbertDataDependent(HilbertSingleRangeCover):
    """A Single-Range-Cover scheme over a mass-balanced 1-D ``2**d``-ary tree of Hilbert distances."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree([self.hilbert_bits], 2**self.dimensions, indexed_mm, weight=self.mass_weight)


class QuadSRCHilbertDataDependentRecords(QuadSRCHilbertDataDependent):
    """:class:`QuadSRCHilbertDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
