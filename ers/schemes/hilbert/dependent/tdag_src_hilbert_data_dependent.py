"""
Data-dependent TDAG-SRC scheme over the Hilbert curve.

The 1-D TDAG of :class:`~ers.schemes.hilbert.tdag_src_hilbert.TdagSRCHilbert`
with both its cut points and its mid-overlap cousins placed by the mass of the
projected curve distances. Single Range Cover of the ``[min, max]`` curve
interval: one token per query. Fills the "TDAG x data-dependent" cell of the
design space, which required a mass-based notion of a chunk's middle for the
cousin placement.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure
from ers.schemes.hilbert.hilbert import HilbertSingleRangeCover
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class TdagSRCHilbertDataDependent(HilbertSingleRangeCover):
    """A Single-Range-Cover scheme over a mass-balanced 1-D TDAG of Hilbert distances."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree([self.hilbert_bits], 2, indexed_mm, mid_overlap=True, weight=self.mass_weight)


class TdagSRCHilbertDataDependentRecords(TdagSRCHilbertDataDependent):
    """:class:`TdagSRCHilbertDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
