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

    def _num_splits_for_dim(self, _: int):
        """
        Returns the number of splits to apply for any given dimension.

        :param _: The dimension index (ignored since the split is uniform).
        :return: The uniform number of splits across all dimensions.
        """
        return self.num_splits