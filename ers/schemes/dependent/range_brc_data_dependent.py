"""
Data-dependent Range-BRC scheme.

:class:`~ers.schemes.range_brc.RangeBRC` with each per-dimension tree cut by
the point mass of that dimension's marginal instead of by length. The cover
rule (Best Range Cover) and exactness are unchanged; what changes is the shape
of the canonical ranges, which now follow the data. The client must keep the
tree (or the statistics to rebuild it) to derive consistent tokens.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree_product
from ers.schemes.common.structured_scheme import BestRangeCover, RangeSupportingStructure
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class RangeBRCDataDependent(BestRangeCover):
    """A Best-Range-Cover scheme over a product of mass-balanced per-dimension trees."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree_product(self.emm_engine.DIMENSIONS_BITS, indexed_mm, weight=self.mass_weight)


class RangeBRCDataDependentRecords(RangeBRCDataDependent):
    """:class:`RangeBRCDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
