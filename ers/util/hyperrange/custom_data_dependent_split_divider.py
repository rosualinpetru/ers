from collections import defaultdict
from typing import List, Dict

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point
from ers.util.hyperrange.custom_uniform_split_divider import CustomUniformSplitDivider
from ers.util.hyperrange.divider import HyperRangeDivider


class CustomDataDependentSplitDivider(HyperRangeDivider):
    """
    A custom HyperRange divider that splits based on the precomputed density of points.
    """

    def __init__(self, num_splits_per_dim: List[int], plaintext_mm: Dict[Point, List[bytes]]):
        self.num_splits_per_dim = num_splits_per_dim
        self.points = plaintext_mm.keys()
        self.uniform = CustomUniformSplitDivider(num_splits_per_dim)

    def _num_splits_for_dim(self, dim: int):
        """
        Returns the number of splits for a given dimension.

        :param dim: The dimension index.
        :return: The number of splits for the given dimension.
        """
        return self.num_splits_per_dim[dim]

    def _compute_point_densities(self, bounding_box: HyperRange) -> dict[int, dict[int, int]]:
        densities = defaultdict(lambda: defaultdict(int))
        for point in self.points:
            if point in bounding_box:
                for dim in range(point.dimensions()):
                    densities[dim][point[dim]] += 1

        return {dim: dict(counts) for dim, counts in densities.items()}

    @staticmethod
    def _divide_segment_by_density(start: int, end: int, dimension_distribution: dict[int, int], splits: int):
        values = list(range(start, end + 1))
        densities = [dimension_distribution.get(i, 0) for i in values]

        cdf = []
        cumulative = 0
        for density in densities:
            cumulative += density
            cdf.append(cumulative)

        total_density = cdf[-1]

        if total_density == 0 or splits <= 0:
            return [(start, end)]  # fallback single segment

        target_densities = [total_density * i // splits for i in range(splits + 1)]

        segment_points = []
        idx = 0
        for target in target_densities:
            while idx < len(cdf) and cdf[idx] < target:
                idx += 1
            segment_points.append(start + idx)

        # Ensure boundaries are within [start, end]
        segment_points[0] = start
        segment_points[-1] = end + 1  # exclusive endpoint for easy segment construction

        # Avoid duplicates and ensure segments are disjoint
        segments = []
        last_point = segment_points[0]
        for point in segment_points[1:]:
            if point <= last_point:
                point = last_point + 1
            segments.append((last_point, point - 1))
            last_point = point

        # Adjust the last segment to end exactly at `end`
        if segments:
            segments[-1] = (segments[-1][0], end)

        return segments

    def divide(self, rng: HyperRange) -> List[HyperRange]:
        if self.num_splits_per_dim is not None:
            assert len(self.num_splits_per_dim) == rng.dimensions

        density = self._compute_point_densities(rng)

        if len(density.keys()) == 0:
            return self.uniform.divide(rng)

        def helper(r: HyperRange, current_dim: int) -> List[HyperRange]:
            if current_dim >= r.dimensions:
                return [r]

            splits_for_this_dim = self._num_splits_for_dim(current_dim)

            if splits_for_this_dim <= 1 or r.start[current_dim] == r.end[current_dim]:
                return helper(r, current_dim + 1)

            split_segments = self._divide_segment_by_density(r.start[current_dim], r.end[current_dim], density.get(current_dim, {}), splits_for_this_dim)

            sub_ranges = []

            for (st, e) in split_segments:
                sub_start_coords = r.start.coords()
                sub_end_coords = r.end.coords()
                sub_start_coords[current_dim] = st
                sub_end_coords[current_dim] = e

                child = HyperRange.from_coords(sub_start_coords, sub_end_coords)
                sub_ranges.append(child)

            results = []
            for sub_rng in sub_ranges:
                results.extend(helper(sub_rng, current_dim + 1))

            return results

        result = helper(rng, 0)
        if rng in result:
            result.remove(rng)
        return result
