"""
Custom data-dependent mid-overlap HyperRange divider.

This divider closes the one structural gap in the divider family: it combines

* **density-based splitting** (:class:`CustomDataDependentSplitDivider`) — cut
  points are placed along the cumulative distribution (CDF) of the indexed
  points, so each child carries roughly equal point *mass* rather than equal
  *length*; and
* **mid-overlap "cousin" nodes** (:class:`CustomUniformSplitMidOverlapDivider`)
  — extra children straddling each seam between two adjacent chunks, which turn
  a range tree into a TDAG and thereby guarantee that every query is contained
  in a *single* node (the property Single-Range-Cover schemes rely on).

The subtlety the combination has to resolve is *where the middle of an uneven
chunk is*. The uniform TDAG places a cousin starting halfway (by length) into
chunk ``i`` and ending halfway into chunk ``i+1``. Here "halfway" is measured
by point mass instead: the cousin runs from the mass-median of chunk ``i`` to
the mass-median of chunk ``i+1``. Equivalently, for a binary split the parent
is cut into four mass-quartiles ``q1 q2 q3 q4``; the children are ``q1+q2`` and
``q3+q4`` and the cousin is ``q2+q3`` — exactly the quartile picture of the
uniform TDAG, transplanted from length-space to mass-space.

Correctness of SRC is preserved for free: the root always contains any query,
and the recursion only ever *adds* covering nodes. What the mass-based cousins
improve is how *small* the single covering node can be on skewed data.

Like the plain data-dependent divider, this one can produce very deep (but
always finite) trees on highly clustered data — every child is strictly
smaller than its parent, but a chunk may shrink by a single cell per level.
Callers that index large domains should raise Python's recursion limit (the
benchmark CLI does).
"""

from typing import Dict, List, Optional, Tuple

from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point
from ers.util.hyperrange.custom_data_dependent_split_divider import CustomDataDependentSplitDivider, MassWeight
from ers.util.hyperrange.custom_uniform_split_mid_overlap_divider import CustomUniformSplitMidOverlapDivider


class CustomDataDependentSplitMidOverlapDivider(CustomDataDependentSplitDivider):
    """
    A HyperRange divider that splits by point density *and* inserts
    mid-overlapping cousin sub-ranges, producing a data-dependent TDAG.

    Inherits the density bookkeeping (per-dimension histograms and CDF-based
    segment splitting) from :class:`CustomDataDependentSplitDivider`; only the
    per-dimension segment list differs, gaining one overlapping segment per
    seam between adjacent chunks.
    """

    def __init__(self, num_splits_per_dim: Optional[List[int]], plaintext_mm: Dict[Point, List[bytes]], weight: MassWeight = "cells"):
        """
        :param num_splits_per_dim: How many chunks to cut each dimension into
            (``None`` if a subclass supplies the count via
            :meth:`_num_splits_for_dim`).
        :param plaintext_mm: The multi-map whose distribution places both the
            split boundaries and the cousin midpoints.
        :param weight: ``"cells"`` to balance occupied cells, ``"records"`` to balance records.
        """
        super().__init__(num_splits_per_dim, plaintext_mm, weight)
        # When a range holds no points there is no density signal; fall back to
        # the uniform TDAG divider so the mid-overlap invariant still holds.
        self.uniform = CustomUniformSplitMidOverlapDivider(num_splits_per_dim)

    def _mass_median_split(self, start: int, end: int, distribution: dict) -> Tuple[int, int]:
        """
        Returns ``(second_half_start, first_half_end)`` of the segment
        ``[start, end]`` when cut at its point-mass median.

        For a single-cell segment both halves are the cell itself.

        :param start: Inclusive lower bound of the segment.
        :param end: Inclusive upper bound of the segment.
        :param distribution: ``{coordinate: count}`` histogram for this dimension.
        :return: The start of the mass-upper half and the end of the mass-lower half.
        """
        if end <= start:
            return start, end
        halves = self._divide_segment_by_density(start, end, distribution, 2)
        # halves == [(start, m), (m', end)] with m < m' guaranteed disjoint.
        return halves[1][0], halves[0][1]

    def _segments_with_overlaps(self, start: int, end: int, distribution: dict, splits: int) -> List[Tuple[int, int]]:
        """
        Cuts ``[start, end]`` into ``splits`` mass-balanced chunks and inserts a
        mass-centred overlapping segment across each seam.

        :param start: Inclusive lower bound of the segment.
        :param end: Inclusive upper bound of the segment.
        :param distribution: ``{coordinate: count}`` histogram for this dimension.
        :param splits: The desired number of (non-overlapping) chunks.
        :return: The chunk segments interleaved with their seam-straddling
            cousins, in coordinate order.
        """
        base = self._divide_segment_by_density(start, end, distribution, splits)

        result: List[Tuple[int, int]] = []
        for i, chunk in enumerate(base):
            result.append(chunk)
            if i == len(base) - 1:
                continue

            nxt = base[i + 1]
            overlap_start, _ = self._mass_median_split(chunk[0], chunk[1], distribution)
            _, overlap_end = self._mass_median_split(nxt[0], nxt[1], distribution)
            overlap = (overlap_start, overlap_end)

            # A cousin equal to the whole parent segment (both outer halves
            # empty) would recreate the parent and never terminate; a cousin
            # equal to an existing chunk adds nothing. Skip both.
            if overlap == (start, end) or overlap in base:
                continue
            result.append(overlap)

        return result

    def divide(self, rng: HyperRange) -> List[HyperRange]:
        """
        Recursively divides a HyperRange into mass-balanced chunks plus
        mid-overlapping cousins, dimension by dimension (product form).

        Falls back to the uniform mid-overlap divider when no indexed point
        lies inside ``rng`` (no density signal), so the TDAG single-cover
        invariant holds everywhere in the domain.

        :param rng: The HyperRange to be divided.
        :return: A list of sub-ranges (excluding ``rng`` itself) after division.
        """
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

            segments = self._segments_with_overlaps(
                r.start[current_dim],
                r.end[current_dim],
                density.get(current_dim, {}),
                splits_for_this_dim,
            )

            results = []
            for st, e in segments:
                sub_start_coords = r.start.coords()
                sub_end_coords = r.end.coords()
                sub_start_coords[current_dim] = st
                sub_end_coords[current_dim] = e
                results.extend(helper(HyperRange.from_coords(sub_start_coords, sub_end_coords), current_dim + 1))

            return results

        result = helper(rng, 0)
        if rng in result:
            result.remove(rng)
        return result
