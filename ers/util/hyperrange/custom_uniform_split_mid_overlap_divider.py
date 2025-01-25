from typing import List

from ers.structures.hyperrange import HyperRange
from ers.util.hyperrange.divider import HyperRangeDivider


class CustomUniformSplitMidOverlapDivider(HyperRangeDivider):
    def __init__(self, num_splits_per_dim: List[int]):
        self.num_splits_per_dim = num_splits_per_dim

    def _num_splits_for_dim(self, dim: int):
        return self.num_splits_per_dim[dim]

    def divide(self, rng: HyperRange) -> List[HyperRange]:
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
                this_size = chunk_size + (1 if i < remainder else 0)
                if this_size <= 0:
                    break

                sub_range_start = current_start
                sub_range_end = current_start + this_size - 1

                # Build coords for the new range
                sub_start_coords = r.start.coords()
                sub_end_coords = r.end.coords()
                sub_start_coords[current_dim] = sub_range_start
                sub_end_coords[current_dim] = sub_range_end

                child = HyperRange.from_coords(sub_start_coords, sub_end_coords)
                sub_ranges.append(child)

                current_start = sub_range_end + 1

            offset_ranges = []
            i = 0
            while True:
                if i >= len(sub_ranges) - 1:
                    break

                # For each chunk i (except the last), create an offset sub-range
                # that starts halfway into chunk i, with the same length as chunk i.
                sub_rng = sub_ranges[i]
                sub_start = sub_rng.start[current_dim]
                sub_end = sub_rng.end[current_dim]

                this_size = sub_end - sub_start + 1
                offset_start = sub_start + (this_size // 2)
                offset_end = offset_start + this_size - 1

                # Only add if it doesn't exceed the dimension boundary
                if offset_end <= end_val:
                    offset_start_coords = r.start.coords()
                    offset_end_coords = r.end.coords()
                    offset_start_coords[current_dim] = offset_start
                    offset_end_coords[current_dim] = offset_end

                    offset_child = HyperRange.from_coords(offset_start_coords, offset_end_coords)
                    if not offset_child in sub_ranges:
                        sub_ranges.insert(i + 1, offset_child)
                        i = i + 1

                i = i + 1

            results = []
            for sr in sub_ranges:
                results.extend(helper(sr, current_dim + 1))

            return results

        return helper(rng, 0)
