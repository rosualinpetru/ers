"""
The Lean formalisation (``lean/Ers``) proves properties of *its own* model of
the segment algorithm and of the dividers. These tests pin the model to the
implementation: the simplified segment rule used in Lean (``segments``, the
paper's Algorithm 1 at tolerance 0) must produce exactly what
``HilbertCurve.brc_with_merging(q, 0)`` produces, on real curves in 2D and 3D,
and the implemented dividers must satisfy the three ``Divider.Good``
properties the Lean lemma assumes.
"""

import random

import pytest

from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point
from ers.util.hyperrange.data_dependent_split_divider import DataDependentSplitDivider
from ers.util.hyperrange.data_dependent_split_mid_overlap_divider import DataDependentSplitMidOverlapDivider
from ers.util.hyperrange.uniform_split_divider import UniformSplitDivider
from ers.util.hyperrange.uniform_split_mid_overlap_divider import UniformSplitMidOverlapDivider
from tests.helpers import random_queries


def lean_segments(inside, boundary):
    """``Ers.Segments.segments``: extend over the next boundary distance iff the next curve cell is inside."""
    if not boundary:
        return []
    out = []
    s = e = boundary[0]
    for b in boundary[1:]:
        if inside(e + 1):
            e = b
        else:
            out.append((s, e))
            s = e = b
    out.append((s, e))
    return out


@pytest.mark.parametrize("dimensions,order", [(2, 3), (2, 4), (3, 2), (3, 3)])
def test_lean_segment_rule_matches_implementation(dimensions, order):
    hc = HilbertCurve(order, dimensions)
    for q in random_queries(order, dimensions, n=80, seed=order * 10 + dimensions):
        boundary = sorted(hc.distances_from_points(q.boundary_points()))
        got = lean_segments(lambda x: q.contains_point(hc.point_from_distance(x)) if x < 2 ** (dimensions * order) else False, boundary)
        assert got == hc.brc_with_merging(q, 0)


def _check_good(divider, bits, n_nodes=300, seed=0):
    """``Divider.Good``: children are strictly shorter sub-intervals covering a non-singleton parent; cells are leaves."""
    rng = random.Random(seed)
    for _ in range(n_nodes):
        lo, hi = sorted((rng.randrange(2**bits), rng.randrange(2**bits)))
        v = HyperRange.from_coords([lo], [hi])
        children = divider.divide(v)
        if lo == hi:
            assert children == []
            continue
        assert children, f"non-singleton {v} must divide"
        covered = set()
        for w in children:
            assert w in v and w.start[0] <= w.end[0]
            assert w.volume() < v.volume()
            covered.update(range(w.start[0], w.end[0] + 1))
        assert covered == set(range(lo, hi + 1))


@pytest.mark.parametrize("bits", [5, 7])
def test_implemented_dividers_are_good(bits):
    mm = {Point([x]): [b"r"] * (1 + (x % 3)) for x in random.Random(bits).sample(range(2**bits), 2**bits // 2)}
    _check_good(UniformSplitDivider(2), bits)
    _check_good(UniformSplitMidOverlapDivider(2), bits)
    for weight in ("cells", "records"):
        _check_good(DataDependentSplitDivider(2, mm, weight), bits)
        _check_good(DataDependentSplitMidOverlapDivider(2, mm, weight), bits)
