"""
Correctness: every scheme must return *all* matching records (no false
negatives), in both 2D and 3D. This is the core soundness invariant of a
searchable-encryption range scheme and the guard against regressions in the
Hilbert segment / boundary logic.
"""

import pytest

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.hilbert_rtree_scheme import HilbertRTreeScheme
from ers.schemes.hilbert.linear_hilbert import LinearHilbert
from ers.schemes.hilbert.quad_brc_hilbert import QuadBRCHilbert
from ers.schemes.hilbert.quad_src_hilbert import QuadSRCHilbert
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.schemes.hilbert.tdag_src_hilbert import TdagSRCHilbert
from ers.schemes.linear import Linear
from ers.schemes.quad_brc import QuadBRC
from ers.schemes.quad_src import QuadSRC
from ers.schemes.range_brc import RangeBRC
from ers.schemes.tdag_src import TdagSRC
from tests.helpers import random_queries, sparse_dataset, true_positives

ALL_SCHEMES = [
    Linear,
    RangeBRC,
    TdagSRC,
    QuadBRC,
    QuadSRC,
    LinearHilbert,
    RangeBRCHilbert,
    TdagSRCHilbert,
    QuadBRCHilbert,
    QuadSRCHilbert,
    HilbertRTreeScheme,
]


@pytest.mark.parametrize("dimensions,bits", [(2, 5), (3, 4)])
@pytest.mark.parametrize("scheme_cls", ALL_SCHEMES, ids=lambda c: c.__name__)
def test_no_false_negatives(scheme_cls, dimensions, bits):
    mm = sparse_dataset(bits, dimensions, n_points=250, seed=dimensions)
    scheme = scheme_cls(EMMEngine([bits] * dimensions, dimensions))
    key = scheme.setup(16)
    scheme.build_index(key, mm)

    for q in random_queries(bits, dimensions, n=40, seed=bits):
        tp = true_positives(q, mm)
        results = scheme.resolve(key, scheme.search(scheme.trapdoor(key, q)))
        assert tp.issubset(results), f"{scheme_cls.__name__} dropped true positives in {dimensions}D for query {q}: missing {tp - results}"
