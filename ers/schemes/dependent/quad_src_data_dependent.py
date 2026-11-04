"""
Data-dependent Quad-SRC scheme.

:class:`~ers.schemes.quad_src.QuadSRC` with the single multi-dimensional tree
cut by point mass instead of by length. Queries use the Single Range Cover:
one token for the smallest node containing the whole query.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree
from ers.schemes.common.structured_scheme import RangeSupportingStructure, SingleRangeCover
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class QuadSRCDataDependent(SingleRangeCover):
    """A Single-Range-Cover scheme over a single mass-balanced quadtree-style tree."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree(self.emm_engine.DIMENSIONS_BITS, 2, indexed_mm, weight=self.mass_weight)


class QuadSRCDataDependentRecords(QuadSRCDataDependent):
    """:class:`QuadSRCDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
