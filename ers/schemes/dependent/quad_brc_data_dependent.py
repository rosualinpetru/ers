"""
Data-dependent Quad-BRC scheme.

:class:`~ers.schemes.quad_brc.QuadBRC` with the single multi-dimensional tree
cut by point mass (per dimension, per node) instead of by length. Queries use
the Best Range Cover and remain exact.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree
from ers.schemes.common.structured_scheme import BestRangeCover, RangeSupportingStructure
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class QuadBRCDataDependent(BestRangeCover):
    """A Best-Range-Cover scheme over a single mass-balanced quadtree-style tree."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree(self.emm_engine.DIMENSIONS_BITS, 2, indexed_mm, weight=self.mass_weight)


class QuadBRCDataDependentRecords(QuadBRCDataDependent):
    """:class:`QuadBRCDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
