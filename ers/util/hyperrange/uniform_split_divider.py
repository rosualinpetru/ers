from ers.util.hyperrange.custom_uniform_split_divider import CustomUniformSplitDivider


class UniformSplitDivider(CustomUniformSplitDivider):
    def __init__(self, num_splits: int):
        super().__init__(None)
        self.num_splits = num_splits

    def _num_splits_for_dim(self, _: int):
        return self.num_splits
