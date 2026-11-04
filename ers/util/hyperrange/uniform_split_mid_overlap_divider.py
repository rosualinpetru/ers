"""
Uniform mid-overlap HyperRange divider (same fan-out in every dimension).

Convenience subclass of :class:`CustomUniformSplitMidOverlapDivider` that applies
a single split count to all dimensions. This is the divider that turns a range
tree into a TDAG by adding overlapping "cousin" nodes.
"""

from ers.util.hyperrange.custom_uniform_split_mid_overlap_divider import CustomUniformSplitMidOverlapDivider


class UniformSplitMidOverlapDivider(CustomUniformSplitMidOverlapDivider):
    """
    A variation of `UniformSplitDivider` that introduces mid-overlapping subranges
    to enhance spatial continuity and coverage.

    This class applies the same number of splits across all dimensions but ensures that
    additional subranges are introduced at midpoints between adjacent divisions.
    """

    def __init__(self, num_splits: int):
        """
        Initializes the UniformSplitMidOverlapDivider with the number of splits per dimension.

        :param num_splits: The number of uniform splits to apply across all dimensions,
                           with additional mid-overlapping subranges.
        """
        super().__init__(None)
        self.num_splits = num_splits

    def _num_splits_for_dim(self, dim: int):
        """
        Returns the number of splits to apply for any given dimension.

        :param dim: The dimension index (ignored: the fan-out is uniform).
        :return: The uniform number of splits across all dimensions.
        """
        return self.num_splits
