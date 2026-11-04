"""
Custom data-dependent HyperRange divider.

Partitions a HyperRange so that each resulting chunk carries roughly equal
*mass*, using the empirical distribution of the indexed multi-map. Splitting
along the cumulative distribution (rather than uniformly) places boundaries
close together in dense regions and far apart in sparse ones.

What "mass" means is a parameter (``weight``):

* ``"cells"`` (default, the setting used by every benchmark): every distinct
  occupied point of the multi-map counts once, so chunks hold equally many
  *occupied cells*. On a domain in which every cell is occupied this reduces
  to the uniform split.
* ``"records"``: every point counts as many times as it has records, so chunks
  hold equally many *records* -- the probability-based notion of density.
"""

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from typing import Dict, List, Literal, Optional

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point
from ers.util.hyperrange.custom_uniform_split_divider import CustomUniformSplitDivider
from ers.util.hyperrange.divider import HyperRangeDivider

#: How the data-dependent dividers count mass: occupied cells or records.
MassWeight = Literal["cells", "records"]


class CustomDataDependentSplitDivider(HyperRangeDivider):
    """
    A custom HyperRange divider that splits based on the precomputed density of points.
    """

    def __init__(self, num_splits_per_dim: Optional[List[int]], plaintext_mm: Dict[Point, List[bytes]], weight: MassWeight = "cells"):
        """
        Initializes the divider from a per-dimension split count and the multi-map.

        :param num_splits_per_dim: A list specifying how many chunks each dimension
            should be split into (may be None, in which case a subclass supplies
            the count via :meth:`_num_splits_for_dim`).
        :param plaintext_mm: The multi-map whose distribution places the split boundaries.
        :param weight: ``"cells"`` to balance occupied cells, ``"records"`` to balance records.
        """
        if weight not in ("cells", "records"):
            raise ValueError(f"Unknown mass weight {weight!r}: expected 'cells' or 'records'")
        self.num_splits_per_dim = num_splits_per_dim
        self.weight = weight
        self.points = list(plaintext_mm.keys())
        self._mass = {p: (len(vals) if weight == "records" else 1) for p, vals in plaintext_mm.items()}
        self.uniform = CustomUniformSplitDivider(num_splits_per_dim)

        # Fast path for one-dimensional dividers (per-dimension range trees and
        # Hilbert-domain trees, i.e. every divider built over projected 1-D
        # points): keep the coordinates sorted once (repeated by mass), so each
        # divide() call can locate the points inside a range with two binary
        # searches and only touch that slice. This turns tree construction from
        # O(#points * #nodes) into O(#points * depth) overall.
        if self.points and self.points[0].dimensions() == 1:
            self._sorted_coords_1d: Optional[List[int]] = sorted(c for p in self.points for c in [p[0]] * self._mass[p])
        else:
            self._sorted_coords_1d = None

    def _num_splits_for_dim(self, dim: int):
        """
        Returns the number of splits for a given dimension.

        :param dim: The dimension index.
        :return: The number of splits for the given dimension.
        """
        assert self.num_splits_per_dim is not None, "subclasses without a per-dim list must override this"
        return self.num_splits_per_dim[dim]

    def _compute_point_densities(self, bounding_box: HyperRange) -> dict[int, dict[int, int]]:
        """
        Builds a per-dimension histogram of point coordinates inside a bounding box.

        :param bounding_box: The HyperRange to which points are restricted.
        :return: A mapping ``dim -> {coordinate: count}`` giving, for each
            dimension, how many points fall on each coordinate value.
        """
        # 1-D fast path: two binary searches bound the coordinates inside the
        # box; only that slice is histogrammed.
        if self._sorted_coords_1d is not None and bounding_box.dimensions == 1:
            lo = bisect_left(self._sorted_coords_1d, bounding_box.start[0])
            hi = bisect_right(self._sorted_coords_1d, bounding_box.end[0])
            if lo == hi:
                return {}
            return {0: dict(Counter(self._sorted_coords_1d[lo:hi]))}

        # Accumulate a 1D marginal histogram per dimension over the enclosed points.
        densities = defaultdict(lambda: defaultdict(int))
        for point in self.points:
            if point in bounding_box:
                for dim in range(point.dimensions()):
                    densities[dim][point[dim]] += self._mass[point]

        return {dim: dict(counts) for dim, counts in densities.items()}

    @staticmethod
    def _divide_segment_by_density(start: int, end: int, dimension_distribution: dict[int, int], splits: int):
        """
        Splits the 1D segment ``[start, end]`` into ``splits`` density-balanced pieces.

        Boundaries are chosen along the cumulative distribution of the point
        density so that every resulting segment carries approximately the same
        share of points; this clusters cut points in dense regions.

        :param start: Inclusive lower bound of the segment.
        :param end: Inclusive upper bound of the segment.
        :param dimension_distribution: A ``{coordinate: count}`` histogram for this dimension.
        :param splits: The desired number of output segments.
        :return: A list of disjoint ``(segment_start, segment_end)`` tuples covering
            ``[start, end]``.
        """
        # If there are fewer values than requested splits, emit one segment per value.
        if splits >= end - start + 1:
            return [(i, i) for i in range(start, end + 1)]

        values = list(range(start, end + 1))
        densities = [dimension_distribution.get(i, 0) for i in values]

        # Compute cumulative distribution function (CDF) of the density.
        cdf = []
        cumulative = 0
        for density in densities:
            cumulative += density
            cdf.append(cumulative)

        total_density = cdf[-1]

        # Equally spaced density targets: the i-th cut aims for i/splits of the mass.
        target_densities = [total_density * i // splits for i in range(splits + 1)]

        segment_points = [start]  # First point is always `start`

        idx = 0
        for i in range(1, splits):  # We already placed `start`, and will place `end` last
            remaining_needed = splits + 1 - len(segment_points)  # Points still needed

            # Advance until the CDF reaches this target, leaving room for the
            # remaining boundaries so every later segment is non-empty.
            while cdf[idx] < target_densities[i] and (end - (start + idx)) >= remaining_needed:
                idx += 1

            next_point = start + idx
            segment_points.append(next_point)
            idx += 1

        segment_points.append(end)

        # Construct segments
        # Avoid duplicates and ensure segments are disjoint
        segments = []
        last_point = segment_points[0]
        for point in segment_points[1:]:
            segments.append((last_point, point))
            last_point = point + 1

        # Adjust the last segment to end exactly at end
        if segments:
            segments[-1] = (segments[-1][0], end)

        for f, s in segments:
            assert f <= s

        return segments

    def divide(self, rng: HyperRange) -> List[HyperRange]:
        """
        Recursively divides a HyperRange into density-balanced sub-ranges.

        Each dimension is cut along its point-density CDF; dimensions are handled
        one after another so the sub-ranges form the product of the per-dimension
        splits. If no points fall inside ``rng``, it falls back to a uniform split.

        :param rng: The HyperRange to be divided.
        :return: A list of sub-ranges (excluding ``rng`` itself) after division.
        """
        if self.num_splits_per_dim is not None:
            assert len(self.num_splits_per_dim) == rng.dimensions

        density = self._compute_point_densities(rng)

        # No enclosed points means no density signal: fall back to a uniform split.
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

            for st, e in split_segments:
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
