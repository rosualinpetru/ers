"""
Data-dependent TDAG-SRC scheme.

:class:`~ers.schemes.tdag_src.TdagSRC` with each per-dimension TDAG cut by
point mass: the chunk boundaries follow the marginal CDF and the mid-overlap
cousin nodes are centred on mass rather than on length. Cousins still straddle
every seam, so the Single-Range-Cover guarantee (one token per query) is
preserved; on skewed data the covering node can hug the data more tightly.
"""

from typing import Dict, List

from ers.schemes.common.structure_builders import data_dependent_tree_product
from ers.schemes.common.structured_scheme import RangeSupportingStructure, SingleRangeCover
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight


class TdagSRCDataDependent(SingleRangeCover):
    """A Single-Range-Cover scheme over a product of mass-balanced per-dimension TDAGs."""

    #: How the divider counts mass: occupied cells (default) or records.
    mass_weight: MassWeight = "cells"

    def _build_structure(self, indexed_mm: Dict[Point, List[bytes]]) -> RangeSupportingStructure:
        return data_dependent_tree_product(self.emm_engine.DIMENSIONS_BITS, indexed_mm, mid_overlap=True, weight=self.mass_weight)


class TdagSRCDataDependentRecords(TdagSRCDataDependent):
    """:class:`TdagSRCDataDependent` balancing records instead of occupied cells."""

    mass_weight = "records"
