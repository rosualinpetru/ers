"""
Tests for the schemes and dividers that complete the design-space matrix:

* ``DataDependentSplitMidOverlapDivider`` — the mass-based TDAG divider
  (segment soundness, cousin invariants, termination on clustered data);
* ``TdagSRCDataDependent`` / ``TdagSRCHilbertDataDependent`` — single-token
  correctness and no false negatives;
* ``InteractiveSRCNative`` — full two-round protocol correctness, exactness
  with a BRC second round, and the rank codec round-trip;
* ``STRRTree`` / ``RTreeScheme`` — packing soundness and no false negatives;
* the per-dimension marginal regression for ``RangeBRCDataDependent``.

Every correctness test checks the *no-false-negatives* invariant against a
brute-force ground truth; SRC-style schemes additionally pin their single-token
property.
"""

import random
import sys

import pytest

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.dependent.range_brc_data_dependent import RangeBRCDataDependent
from ers.schemes.dependent.tdag_src_data_dependent import TdagSRCDataDependent
from ers.schemes.hilbert.dependent.tdag_src_hilbert_data_dependent import TdagSRCHilbertDataDependent
from ers.schemes.interactive.interactive_src_native import InteractiveSRCNative
from ers.schemes.rtree_scheme import RTreeScheme
from ers.structures.hyperrange import HyperRange
from ers.structures.hyperrange_tree_product import HyperRangeTreeProduct
from ers.structures.point import Point
from ers.structures.str_rtree import STRRTree
from ers.util.hyperrange.data_dependent_split_mid_overlap_divider import DataDependentSplitMidOverlapDivider
from tests.helpers import random_queries, sparse_dataset, true_positives

# Data-dependent trees can degenerate into deep chains on clustered data.
sys.setrecursionlimit(100_000)


def clustered_dataset(bits: int, dimensions: int, n_points: int, seed: int = 0):
    """A deliberately skewed multi-map: most mass in one corner cluster."""
    rng = random.Random(seed)
    bound = 2**bits
    mm = {}
    for i in range(n_points):
        if i % 4 == 0:  # a quarter of the points spread uniformly
            coords = [rng.randrange(bound) for _ in range(dimensions)]
        else:  # the rest packed into a small corner cluster
            coords = [rng.randrange(max(2, bound // 8)) for _ in range(dimensions)]
        p = Point(coords)
        mm.setdefault(p, []).append(("d%d" % i).encode())
    return mm


# --------------------------------------------------------------------------- #
# DataDependentSplitMidOverlapDivider invariants.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("seed", range(5))
def test_dd_mid_overlap_children_sound(seed):
    """Children must cover the parent, stay inside it, and be strictly smaller."""
    mm = clustered_dataset(6, 1, 200, seed=seed)
    divider = DataDependentSplitMidOverlapDivider(2, mm)
    rng = HyperRange.from_bits([6])
    children = divider.divide(rng)

    assert children, "root must divide"
    covered = set()
    for c in children:
        assert c in rng, "child escapes the parent"
        assert c != rng, "child equal to parent would never terminate"
        covered.update(range(c.start[0], c.end[0] + 1))
    # The (non-cousin) chunks alone must already cover the parent segment.
    assert covered == set(range(rng.start[0], rng.end[0] + 1))


def test_dd_mid_overlap_has_seam_cousin():
    """A seam between two chunks must be straddled by a cousin node."""
    # Uniform-ish data so the split is non-degenerate and a cousin is expected.
    mm = {Point([i]): [b"x"] for i in range(0, 64)}
    divider = DataDependentSplitMidOverlapDivider(2, mm)
    children = divider.divide(HyperRange.from_bits([6]))

    # Every internal chunk boundary (a "seam") must be strictly straddled by
    # some child — the cousin that guarantees the SRC single-cover property.
    cut_points = {c.end[0] for c in children if c.end[0] < 63}
    assert cut_points, "expected at least one internal seam"
    for cut in cut_points:
        assert any(c.start[0] <= cut < c.end[0] for c in children), f"no cousin straddles the seam at {cut}"


def test_dd_mid_overlap_terminates_on_clustered_data():
    """Tree construction must terminate even on heavily clustered data."""
    from ers.structures.hyperrange_tree import HyperRangeTree

    mm = clustered_dataset(7, 1, 300, seed=3)
    tree = HyperRangeTree.init(HyperRange.from_bits([7]), DataDependentSplitMidOverlapDivider(2, mm))
    assert tree.height >= 1


# --------------------------------------------------------------------------- #
# Data-dependent TDAG-SRC schemes: single token, no false negatives.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("dimensions,bits", [(2, 5), (3, 3)])
def test_tdag_src_data_dependent_correct(dimensions, bits):
    mm = clustered_dataset(bits, dimensions, 250, seed=dimensions)
    scheme = TdagSRCDataDependent(EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dimensions, n=30, seed=bits):
        tds = scheme.trapdoor(key, q)
        assert len(tds) == 1, "SRC must issue exactly one token"
        got = scheme.resolve(key, scheme.search(tds))
        assert true_positives(q, mm).issubset(got)


@pytest.mark.parametrize("dimensions,bits", [(2, 5), (3, 3)])
def test_tdag_src_hilbert_data_dependent_correct(dimensions, bits):
    mm = clustered_dataset(bits, dimensions, 250, seed=dimensions + 1)
    scheme = TdagSRCHilbertDataDependent(EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dimensions, n=30, seed=bits + 1):
        tds = scheme.trapdoor(key, q)
        assert len(tds) == 1, "SRC must issue exactly one token"
        got = scheme.resolve(key, scheme.search(tds))
        assert true_positives(q, mm).issubset(got)


def test_tdag_src_dd_not_worse_than_uniform_on_clusters():
    """
    On clustered data the mass-adapted TDAG's single cover should not return
    more results (false positives) on average than the uniform TDAG's.
    """
    from ers.schemes.tdag_src import TdagSRC

    bits, dims = 5, 2
    mm = clustered_dataset(bits, dims, 300, seed=9)

    dd = TdagSRCDataDependent(EMMEngine([bits] * dims, dims))
    kd = dd.setup(16)
    dd.build_index(kd, mm)
    un = TdagSRC(EMMEngine([bits] * dims, dims))
    ku = un.setup(16)
    un.build_index(ku, mm)

    dd_total = un_total = 0
    for q in random_queries(bits, dims, n=40, seed=11):
        dd_total += len(dd.search(dd.trapdoor(kd, q)))
        un_total += len(un.search(un.trapdoor(ku, q)))
    assert dd_total <= un_total * 1.10  # allow 10% noise margin


# --------------------------------------------------------------------------- #
# Native interactive scheme.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("dimensions,bits", [(2, 5), (3, 3)])
def test_interactive_native_no_false_negatives(dimensions, bits):
    mm = sparse_dataset(bits, dimensions, 300, seed=dimensions)
    scheme = InteractiveSRCNative(EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dimensions, n=30, seed=bits):
        got = scheme.query(key, q)
        assert true_positives(q, mm).issubset(got)


def test_interactive_native_brc_round2_is_exact():
    """With a BRC second round the interactive scheme has precision exactly 1."""
    bits, dims = 5, 2
    mm = sparse_dataset(bits, dims, 300, seed=21)
    scheme = InteractiveSRCNative(EMMEngine([bits] * dims, dims), single_range_cover_round2=False)
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dims, n=30, seed=22):
        got = scheme.query(key, q)
        assert got == true_positives(q, mm)


def test_interactive_native_rank_codec_roundtrip():
    """The mixed-radix rank encoding must be a bijection on the grid."""
    scheme = InteractiveSRCNative(EMMEngine([3, 2, 4], 3))
    seen = set()
    for x in range(8):
        for y in range(4):
            for z in range(16):
                p = Point([x, y, z])
                r = scheme._value_of(p)
                assert scheme._point_of(r) == p
                seen.add(r)
    assert len(seen) == 8 * 4 * 16
    assert min(seen) == 0 and max(seen) == 8 * 4 * 16 - 1


def test_interactive_native_round1_single_token():
    bits, dims = 5, 2
    mm = sparse_dataset(bits, dims, 200, seed=31)
    scheme = InteractiveSRCNative(EMMEngine([bits] * dims, dims))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dims, n=20, seed=32):
        assert len(scheme.trapdoor_round1(key, q)) == 1


# --------------------------------------------------------------------------- #
# STR R-tree.
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("dimensions,bits", [(2, 6), (3, 4)])
def test_str_rtree_no_false_negatives(dimensions, bits):
    mm = sparse_dataset(bits, dimensions, 400, seed=dimensions)
    scheme = RTreeScheme(EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dimensions, n=40, seed=bits):
        got = scheme.resolve(key, scheme.search(scheme.trapdoor(key, q)))
        assert true_positives(q, mm).issubset(got)


def test_str_packing_covers_all_points_within_capacity():
    """Every point lands in exactly one leaf; all leaves respect capacity."""
    bits, dims, cap = 5, 2, 4
    mm = sparse_dataset(bits, dims, 300, seed=6)
    tree = STRRTree.build(list(mm.keys()), dims, node_capacity=cap)

    leaves = [n for n in tree.all_nodes() if n.is_leaf]
    assert all(len(l.points) <= cap for l in leaves)
    packed = [tuple(p.coords()) for l in leaves for p in l.points]
    assert len(packed) == len(set(packed)) == len(mm)
    assert set(packed) == {tuple(p.coords()) for p in mm.keys()}


def test_str_rtree_children_within_parent_bbox():
    bits, dims = 5, 2
    mm = sparse_dataset(bits, dims, 300, seed=8)
    tree = STRRTree.build(list(mm.keys()), dims, node_capacity=4)
    assert tree.root is not None
    stack = [tree.root]
    while stack:
        n = stack.pop()
        for c in n.children:
            assert c.bbox in n.bbox
            stack.append(c)


def test_str_rtree_empty_dataset():
    tree = STRRTree.build([], 2, node_capacity=4)
    assert tree.root is None
    assert tree.cover(HyperRange.from_bits([4, 4])) == []
    assert tree.all_nodes() == []


# --------------------------------------------------------------------------- #
# Regression: per-dimension marginals in RangeBRCDataDependent.
# --------------------------------------------------------------------------- #
def test_range_brc_dd_adapts_each_dimension_to_its_own_marginal():
    """
    Dimension 0 is uniform; dimension 1 is heavily clustered near 0. The
    dimension-1 tree's first cut must reflect dimension 1's skew (cut well
    below the uniform midpoint), which fails if all trees are (incorrectly)
    fed dimension 0's marginal.
    """
    bits = 6
    rng = random.Random(42)
    mm = {}
    for i in range(400):
        x = rng.randrange(2**bits)  # uniform in dim 0
        y = rng.randrange(4)  # clustered near 0 in dim 1
        mm.setdefault(Point([x, y]), []).append(b"p%d" % i)

    scheme = RangeBRCDataDependent(EMMEngine([bits, bits], 2))
    key = scheme.setup(16)
    scheme.build_index(key, mm)

    assert isinstance(scheme.structure, HyperRangeTreeProduct)
    dim1_tree = scheme.structure.trees[1]
    # The root's children partition dim 1; the first (mass-lower) child must
    # end far below the uniform midpoint of 31 because ~all mass is in [0, 3].
    first_child_end = min(c.rng.end[0] for c in dim1_tree.children)
    assert first_child_end < 8, "dimension-1 tree ignored its own marginal (first cut at %d)" % first_child_end

    # And correctness must hold as always.
    for q in random_queries(bits, 2, n=20, seed=43):
        got = scheme.resolve(key, scheme.search(scheme.trapdoor(key, q)))
        assert true_positives(q, mm).issubset(got)


# --------------------------------------------------------------------------- #
# Mass weighting of the data-dependent dividers.
# --------------------------------------------------------------------------- #
def test_cell_weighting_reduces_to_uniform_when_every_cell_is_occupied():
    """With one record per cell everywhere, "cells" mass is flat: cuts are the uniform ones."""
    from ers.schemes.common.structure_builders import data_dependent_tree, uniform_tree

    mm = {Point([i]): [b"r"] for i in range(64)}
    dd = data_dependent_tree([6], 2, mm)
    un = uniform_tree([6], 2)
    assert {n.rng for n in dd.nodes()} == {n.rng for n in un.nodes()}


def test_record_weighting_follows_the_records():
    """With "records" mass, a cell holding most records pulls the first cut towards it."""
    from ers.schemes.common.structure_builders import data_dependent_tree

    mm = {Point([i]): [b"r"] * (100 if i < 4 else 1) for i in range(64)}
    cells = data_dependent_tree([6], 2, mm, weight="cells")
    records = data_dependent_tree([6], 2, mm, weight="records")
    assert max(c.rng.end[0] for c in cells.children) == 63 and min(c.rng.end[0] for c in cells.children) == 31
    assert min(c.rng.end[0] for c in records.children) < 8


def test_unknown_weight_is_rejected():
    from ers.util.hyperrange.data_dependent_split_divider import DataDependentSplitDivider

    with pytest.raises(ValueError):
        DataDependentSplitDivider(2, {Point([0]): [b"r"]}, weight="volume")  # type: ignore[arg-type]


def test_records_variants_are_registered_and_sound():
    """Every record-weighted variant declares the weighting and returns all true positives."""
    from ers.benchmark.cli import schemes

    names = [n for n in schemes if n.endswith("_records")]
    assert len(names) == 8
    bits, dims = 5, 2
    mm = clustered_dataset(bits, dims, 250, seed=5)
    for name in names:
        scheme = schemes[name](EMMEngine([bits] * dims, dims))
        assert scheme.mass_weight == "records"
        key = scheme.setup(16)
        scheme.build_index(key, mm)
        for q in random_queries(bits, dims, n=10, seed=6):
            got = scheme.resolve(key, scheme.search(scheme.trapdoor(key, q)))
            assert true_positives(q, mm).issubset(got), name


def test_range_cover_pruning_matches_exhaustive_cover():
    """Pruning disjoint vertices must not change the cover of a range tree or a TDAG."""
    from ers.schemes.common.structure_builders import uniform_tree

    for mid in (False, True):
        tree = uniform_tree([7], 2, mid_overlap=mid)
        for q in random_queries(7, 1, n=40, seed=3):
            cover = tree.brc(q)
            covered = {c for r in cover for c in range(r.start[0], r.end[0] + 1)}
            assert covered == set(range(q.start[0], q.end[0] + 1))
            # maximality holds for a tree; a TDAG reaches the same cell through
            # a cousin and a sibling, so its BRC is sound but not minimal.
            if not mid:
                assert not any(a != b and a in b for a in cover for b in cover)
