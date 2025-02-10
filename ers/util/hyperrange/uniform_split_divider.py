from ers.util.hyperrange.custom_uniform_split_divider import CustomUniformSplitDivider


class UniformSplitDivider(CustomUniformSplitDivider):
    """
    A specialized HyperRange divider that uniformly splits a given range across all dimensions.

    Unlike `CustomUniformSplitDivider`, this class applies the same number of splits to every dimension,
    ensuring consistent partitioning of the space.
    """

    def __init__(self, num_splits: int):
        """
        Initializes the UniformSplitDivider with the number of splits per dimension.

        :param num_splits: The number of uniform splits to apply across all dimensions.
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