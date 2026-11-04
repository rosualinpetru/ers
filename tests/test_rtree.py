"""
The packed Hilbert R-tree must be sound (no false negatives) and, averaged over
queries, must not emit more search tokens than the binary-tree RangeBRCHilbert
baseline — the property that motivates it.
"""

import statistics as st

import pytest

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert_rtree_scheme import HilbertRTreeScheme
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.structures.hilbert_rtree import HilbertRTree
from tests.helpers import random_queries, sparse_dataset, true_positives


@pytest.mark.parametrize("dimensions,bits", [(2, 6), (3, 4)])
def test_rtree_no_false_negatives(dimensions, bits):
    mm = sparse_dataset(bits, dimensions, n_points=400, seed=dimensions)
    scheme = HilbertRTreeScheme(EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dimensions, n=40, seed=bits):
        tp = true_positives(q, mm)
        got = scheme.resolve(key, scheme.search(scheme.trapdoor(key, q)))
        assert tp.issubset(got)


def test_rtree_uses_no_more_tokens_than_binary_tree():
    bits, dims = 6, 2
    mm = sparse_dataset(bits, dims, n_points=600, seed=5)
    rt = HilbertRTreeScheme(EMMEngine([bits] * dims, dims))
    k = rt.setup(16)
    rt.build_index(k, mm)
    brc = RangeBRCHilbert(EMMEngine([bits] * dims, dims))
    kb = brc.setup(16)
    brc.build_index(kb, mm)

    tok_rt, tok_brc = [], []
    for q in random_queries(bits, dims, n=60, seed=7):
        tok_rt.append(len(rt.trapdoor(k, q)))
        tok_brc.append(len(brc.trapdoor(kb, q)))
    assert st.mean(tok_rt) <= st.mean(tok_brc)


def test_packed_tree_covers_all_points():
    """Every indexed point lands in exactly the leaves under the root's cover."""
    bits, dims = 5, 2
    mm = sparse_dataset(bits, dims, n_points=300, seed=6)
    tree = HilbertRTree.build(list(mm.keys()), dims, bits, node_capacity=4)
    assert tree.root is not None
    packed = {tuple(p.coords()) for p in tree.root.subtree_points()}
    assert packed == {tuple(p.coords()) for p in mm.keys()}
