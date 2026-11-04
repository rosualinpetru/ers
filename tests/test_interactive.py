"""
The interactive double-index scheme must be sound (no false negatives) and must
improve precision over the non-interactive Hilbert SRC baseline: SRC round two
matches or beats the baseline, and BRC round two is exact (precision 1).
"""

import statistics as st

import pytest

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.interactive_src_hilbert import InteractiveSRCHilbert
from ers.schemes.hilbert.tdag_src_hilbert import TdagSRCHilbert
from ers.schemes.interactive.interactive_src import InteractiveSRC
from tests.helpers import random_queries, sparse_dataset, true_positives


@pytest.mark.parametrize("dimensions,bits", [(1, 6), (2, 5), (3, 4)])
def test_interactive_no_false_negatives(dimensions, bits):
    mm = sparse_dataset(bits, dimensions, n_points=250, seed=dimensions)
    scheme_cls = InteractiveSRC if dimensions == 1 else InteractiveSRCHilbert
    scheme = scheme_cls(EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dimensions, n=40, seed=bits):
        tp = true_positives(q, mm)
        assert tp.issubset(scheme.query(key, q))


def test_brc_round_two_is_exact():
    """With a BRC second round the interactive scheme has precision 1."""
    bits, dims = 5, 2
    mm = sparse_dataset(bits, dims, n_points=300, seed=2)
    scheme = InteractiveSRCHilbert(EMMEngine([bits] * dims, dims), single_range_cover_round2=False)
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dims, n=40, seed=9):
        tp = true_positives(q, mm)
        got = scheme.query(key, q)
        assert tp.issubset(got)
        if got:
            assert got == tp  # no false positives either


def test_interaction_beats_non_interactive_precision():
    """Averaged over queries, interaction is at least as precise as the baseline."""
    bits, dims = 5, 2
    mm = sparse_dataset(bits, dims, n_points=400, seed=3)
    inter = InteractiveSRCHilbert(EMMEngine([bits] * dims, dims))
    ki = inter.setup(16)
    inter.build_index(ki, mm)
    base = TdagSRCHilbert(EMMEngine([bits] * dims, dims))
    kb = base.setup(16)
    base.build_index(kb, mm)

    p_inter, p_base = [], []
    for q in random_queries(bits, dims, n=60, seed=11):
        tp = true_positives(q, mm)
        if not tp:
            continue
        gi = inter.query(ki, q)
        gb = base.resolve(kb, base.search(base.trapdoor(kb, q)))
        p_inter.append(len(tp) / len(gi) if gi else 1.0)
        p_base.append(len(tp) / len(gb) if gb else 1.0)

    assert st.mean(p_inter) >= st.mean(p_base)
    assert st.mean(p_inter) > st.mean(p_base) + 0.05  # a real, not marginal, gain


def test_query_with_metrics_matches_query_and_reports_rounds():
    """The dashboard adapter returns the same documents as query() plus a
    consistent per-round metric breakdown."""
    bits, dims = 5, 2
    mm = sparse_dataset(bits, dims, n_points=300, seed=4)
    scheme = InteractiveSRCHilbert(EMMEngine([bits] * dims, dims))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    for q in random_queries(bits, dims, n=30, seed=13):
        docs_plain = scheme.query(key, q)
        docs, m = scheme.query_with_metrics(key, q)
        assert docs == docs_plain
        assert m["rounds"] == 2
        assert m["trapdoor_count"] == m["trapdoor_count_round1"] + m["trapdoor_count_round2"]
        assert m["trapdoor_count_round1"] in (0, 1)  # round one is a single SRC token
        for t in ("trapdoor_time", "search_time", "resolve_time"):
            assert m[t] >= 0
