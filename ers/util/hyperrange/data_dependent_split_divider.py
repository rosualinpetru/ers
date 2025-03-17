from typing import Dict, List

from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import CustomDataDependentSplitDivider
from ers.util.hyperrange.uniform_split_divider import UniformSplitDivider


class DataDependentSplitDivider(CustomDataDependentSplitDivider):
    """
    A specialized HyperRange divider that splits a given range across all dimensions based on point density.

    Unlike `CustomUniformSplitDivider`, this class applies the same number of splits to every dimension,
    ensuring consistent partitioning of the space.
    """

    def __init__(self, num_splits: int, plaintext_mm: Dict[Point, List[bytes]]):
        """
        Initializes the DataDependentSplitDivider with the number of splits per dimension.

        :param num_splits: The number of data-dependent splits to apply across all dimensions.
        """
        super().__init__(None, plaintext_mm)
        self.uniform = UniformSplitDivider(num_splits)
        self.num_splits = num_splits

    def _num_splits_for_dim(self, _: int):
        """
        Returns the number of splits to apply for any given dimension.

        :param _: The dimension index (ignored since the split is uniform).
        :return: The uniform number of splits across all dimensions.
        """
        return self.num_splits
