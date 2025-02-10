from typing import List

from ers.structures.hyperrange import HyperRange
from ers.util.hyperrange.divider import HyperRangeDivider


class CustomUniformSplitDivider(HyperRangeDivider):
    """
    A custom HyperRange divider that splits a given range uniformly across each dimension.

    This class takes a predefined number of splits per dimension and recursively divides the given
    HyperRange accordingly. If a dimension cannot be split further, it is left unchanged.
    """

    def __init__(self, num_splits_per_dim: List[int]):
        """
        Initializes the CustomUniformSplitDivider with the number of splits per dimension.

        :param num_splits_per_dim: A list specifying how many times each dimension should be split.
        """
        self.num_splits_per_dim = num_splits_per_dim

    def _num_splits_for_dim(self, dim: int):
        """
        Returns the number of splits for a given dimension.

        :param dim: The dimension index.
        :return: The number of splits for the given dimension.
        """
        return self.num_splits_per_dim[dim]

    def divide(self, rng: HyperRange) -> List[HyperRange]:
        """
        Recursively divides a HyperRange into smaller subranges based on the predefined split strategy.

        :param rng: The HyperRange to be divided.
        :return: A list of subranges after division.
        """
        if self.num_splits_per_dim is not None:
            assert len(self.num_splits_per_dim) == rng.dimensions

        def helper(r: HyperRange, current_dim: int) -> List["HyperRange"]:
            if current_dim >= r.dimensions:
                return [r]

            splits_for_this_dim = self._num_splits_for_dim(current_dim)
            start_val = r.start[current_dim]
            end_val = r.end[current_dim]
            length = end_val - start_val + 1  # inclusive boundary

            if length <= 1 or splits_for_this_dim <= 1:
                return helper(r, current_dim + 1)

            chunk_size = length // splits_for_this_dim
            remainder = length % splits_for_this_dim

            sub_ranges = []
            current_start = start_val

            for i in range(splits_for_this_dim):
                # if there's a remainder left, add 1 to the chunk
                this_size = chunk_size + (1 if i < remainder else 0)

                if this_size <= 0:
                    break  # Stop if no space for further division

                sub_range_start = current_start
                sub_range_end = current_start + this_size - 1

                sub_start_coords = r.start.coords()
                sub_end_coords = r.end.coords()
                sub_start_coords[current_dim] = sub_range_start
                sub_end_coords[current_dim] = sub_range_end

                child = HyperRange.from_coords(sub_start_coords, sub_end_coords)
                sub_ranges.append(child)

                current_start = sub_range_end + 1

            results = []
            for sub_rng in sub_ranges:
                results.extend(helper(sub_rng, current_dim + 1))

            return results

        result = helper(rng, 0)
        if rng in result:
            result.remove(rng)
        return result
