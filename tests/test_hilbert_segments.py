"""
The Hilbert segment cover must be sound: for any tolerance it must contain every
query point (no false negatives), and with tolerance 0 it must be *exact* (no
false positives), in both 2D and 3D.
"""

import pytest

from ers.structures.hilbert_curve import HilbertCurve
from tests.helpers import random_queries


def covered_cells(hc, segments):
    cells = set()
    for lo, hi in segments:
        for d in range(lo, hi + 1):
            cells.add(tuple(hc.point_from_distance(d).coords()))
    return cells


@pytest.mark.parametrize("dimensions,order", [(2, 4), (3, 3)])
@pytest.mark.parametrize("tolerance", [0, 1])
def test_segments_cover_every_query_point(dimensions, order, tolerance):
    hc = HilbertCurve(order, dimensions)
    for q in random_queries(order, dimensions, n=60, seed=order + tolerance):
        segments = hc.brc_with_merging(q, tolerance)
        covered = covered_cells(hc, segments)
        query_pts = {tuple(p.coords()) for p in q.points()}
        assert query_pts.issubset(covered)  # soundness: no false negatives


@pytest.mark.parametrize("dimensions,order", [(2, 4), (3, 3)])
def test_tolerance_zero_is_exact(dimensions, order):
    hc = HilbertCurve(order, dimensions)
    for q in random_queries(order, dimensions, n=60, seed=order):
        covered = covered_cells(hc, hc.brc_with_merging(q, 0))
        query_pts = {tuple(p.coords()) for p in q.points()}
        assert covered == query_pts  # exact: precision 1, no false positives
