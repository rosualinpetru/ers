"""
Data-dependent HyperRange divider (same fan-out in every dimension).

Convenience subclass of :class:`CustomDataDependentSplitDivider` that applies a
single split count to all dimensions. It partitions each dimension so that the
resulting chunks carry roughly equal point mass, falling back to a uniform split
when no points fall inside the range.
"""

from typing import Dict, List

from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import CustomDataDependentSplitDivider, MassWeight
from ers.util.hyperrange.uniform_split_divider import UniformSplitDivider


class DataDependentSplitDivider(CustomDataDependentSplitDivider):
    """
    A specialized HyperRange divider that splits a given range across all dimensions based on point density.

    Unlike `CustomUniformSplitDivider`, this class applies the same number of splits to every dimension,
    ensuring consistent partitioning of the space.
    """

    def __init__(self, num_splits: int, plaintext_mm: Dict[Point, List[bytes]], weight: MassWeight = "cells"):
        """
        Initializes the DataDependentSplitDivider with the number of splits per dimension.

        :param num_splits: The number of data-dependent splits to apply across all dimensions.
        :param plaintext_mm: The multi-map whose distribution places the split boundaries.
        :param weight: ``"cells"`` to balance occupied cells, ``"records"`` to balance records.
        """
        super().__init__(None, plaintext_mm, weight)
        self.uniform = UniformSplitDivider(num_splits)
        self.num_splits = num_splits

    def _num_splits_for_dim(self, dim: int):
        """
        Returns the number of splits to apply for any given dimension.

        :param dim: The dimension index (ignored: the fan-out is uniform).
        :return: The uniform number of splits across all dimensions.
        """
        return self.num_splits
