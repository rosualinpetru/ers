"""
Data-dependent mid-overlap HyperRange divider (same fan-out in every dimension).

Convenience subclass of :class:`CustomDataDependentSplitMidOverlapDivider` that
applies a single split count to all dimensions — the divider that turns a range
tree into a **data-dependent TDAG**: chunks carry roughly equal point mass and
every seam is straddled by a mass-centred cousin node, so Single-Range-Cover
queries stay answerable with one token while the tree shape adapts to the data.
"""

from typing import Dict, List

from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import MassWeight
from ers.util.hyperrange.custom_data_dependent_split_mid_overlap_divider import CustomDataDependentSplitMidOverlapDivider
from ers.util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider


class DataDependentSplitMidOverlapDivider(CustomDataDependentSplitMidOverlapDivider):
    """
    A data-dependent TDAG divider with a uniform number of splits per dimension.
    """

    def __init__(self, num_splits: int, plaintext_mm: Dict[Point, List[bytes]], weight: MassWeight = "cells"):
        """
        :param num_splits: The number of mass-balanced chunks to cut every
            dimension into (cousin overlaps are added on top of these).
        :param plaintext_mm: The multi-map whose distribution places the cuts and cousins.
        :param weight: ``"cells"`` to balance occupied cells, ``"records"`` to balance records.
        """
        super().__init__(None, plaintext_mm, weight)
        self.num_splits = num_splits
        # Point-free ranges fall back to the uniform TDAG divider.
        self.uniform = UniformSplitMidOverlapDivider(num_splits)

    def _num_splits_for_dim(self, dim: int):
        """
        :param dim: The dimension index (ignored: the fan-out is uniform).
        :return: The uniform number of splits for every dimension.
        """
        return self.num_splits
