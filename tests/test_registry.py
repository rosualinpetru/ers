"""
Every scheme registered in the benchmark CLI must be sound end-to-end on the
harness's own datasets: no false negatives, the declared exactness must hold,
single-cover schemes must issue one token, and the 3D NH dataset must be
loaded on integer coordinates (a float coordinate once made the Linear
scheme's labels miss every record).
"""

import sys

import pytest

from ers.benchmark.cli import INTERACTIVE_SCHEMES, schemes
from ers.benchmark.util.dataset_generator import generate_nh_64
from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.common.structured_scheme import SingleRangeCover
from ers.schemes.hilbert.hilbert import HilbertSingleRangeCover
from ers.schemes.linear import Linear
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point
from tests.helpers import random_queries, sparse_dataset, true_positives

sys.setrecursionlimit(100_000)


def run(scheme, key, query):
    if hasattr(scheme, "query"):
        return scheme.query(key, query), None
    tokens = scheme.trapdoor(key, query)
    return scheme.resolve(key, scheme.search(tokens)), tokens


@pytest.mark.parametrize("dimensions,bits", [(2, 5), (3, 3)])
@pytest.mark.parametrize("name", sorted(schemes))
def test_registered_scheme_is_sound(name, dimensions, bits):
    mm = sparse_dataset(bits, dimensions, n_points=200, seed=7)
    scheme = schemes[name](EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)

    for q in random_queries(bits, dimensions, n=25, seed=bits):
        tp = true_positives(q, mm)
        got, tokens = run(scheme, key, q)
        assert tp.issubset(got), f"{name} dropped true positives for {q}"
        if scheme.exact:
            assert got == tp, f"{name} claims exactness but returned false positives for {q}"
        if isinstance(scheme, (SingleRangeCover, HilbertSingleRangeCover)):
            assert tokens is not None and len(tokens) == 1, f"{name} must issue a single token"


def test_interactive_schemes_are_routed_separately():
    assert INTERACTIVE_SCHEMES <= set(schemes)
    for name in INTERACTIVE_SCHEMES:
        assert hasattr(schemes[name], "query_with_metrics")


def test_nh_64_loads_integer_coordinates_and_linear_finds_them():
    raw = generate_nh_64()
    assert all(isinstance(c, int) for coords in raw for c in coords)
    mm = {Point(list(t)): vals for t, vals in list(raw.items())[:300]}

    scheme = Linear(EMMEngine([6, 6, 6], 3))
    key = scheme.setup(16)
    scheme.build_index(key, mm)
    query = HyperRange.from_coords([0, 0, 0], [2, 5, 63])
    tp = true_positives(query, mm)
    assert tp, "the query must hit some records"
    assert scheme.resolve(key, scheme.search(scheme.trapdoor(key, query))) == tp
