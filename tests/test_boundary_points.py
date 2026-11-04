"""
Regression test for the ``HyperRange.boundary_points`` fix.

The Hilbert segment algorithm needs every *surface* cell of a query box (the
cells where the curve can enter or leave the query), not just its edges. An
earlier version returned only the wireframe of edges, which silently dropped
face-interior cells in 3D and caused false negatives in every Hilbert scheme.
These tests pin the surface down exactly.
"""

import itertools

import pytest

from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.hyperrange import HyperRange


def brute_force_surface(start, end):
    """Every cell of the box with at least one coordinate on a face."""
    ranges = [range(start[i], end[i] + 1) for i in range(len(start))]
    surface = set()
    for coords in itertools.product(*ranges):
        if any(coords[i] in (start[i], end[i]) for i in range(len(start))):
            surface.add(coords)
    return surface


@pytest.mark.parametrize(
    "start,end",
    [
        ([1, 1], [4, 3]),  # 2D perimeter
        ([2, 2, 2], [5, 5, 5]),  # 3D full surface (regression case)
        ([0, 0, 0], [3, 7, 2]),  # 3D asymmetric box
        ([3, 3], [3, 3]),  # degenerate single point
    ],
)
def test_boundary_points_are_the_full_surface(start, end):
    q = HyperRange.from_coords(start, end)
    got = {tuple(p.coords()) for p in q.boundary_points()}
    assert got == brute_force_surface(start, end)


@pytest.mark.parametrize("order", [3, 4])
def test_hilbert_src_covers_every_query_point_in_3d(order):
    """A direct SRC over the 3D Hilbert curve must contain all query points."""
    hc = HilbertCurve(order, 3)
    import random

    rng = random.Random(order)
    bound = 2**order
    for _ in range(80):
        c = [rng.randrange(bound) for _ in range(3)]
        d = [rng.randrange(bound) for _ in range(3)]
        start = [min(a, b) for a, b in zip(c, d)]
        end = [max(a, b) for a, b in zip(c, d)]
        q = HyperRange.from_coords(start, end)
        lo, hi = hc.src(q)
        covered = {tuple(hc.point_from_distance(x).coords()) for x in range(lo, hi + 1)}
        query_pts = {tuple(p.coords()) for p in q.points()}
        assert query_pts.issubset(covered)
