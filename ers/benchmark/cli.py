"""
Benchmark command-line interface.

Usage::

    python3 -m ers.benchmark.cli --scheme range_brc --dataset cali \
        --domain-size 6 --records-limit 1000000 --queries-count 250

Builds the chosen scheme over the dataset scaled to ``2**domain_size`` cells
per dimension, runs the bucketed query workload, and writes an ``.xlsx``
report under ``benchmarks/`` named
``<scheme>_<dataset>_<dims>_<bits>_<records>_<queries>_<timestamp>.xlsx``.
"""

import argparse
import sys
from argparse import Namespace
from datetime import datetime

from ers.benchmark.benchmark import run_benchmark, run_interactive_benchmark
from ers.benchmark.util.dataset_generator import (
    generate_cali,
    generate_dense_database_2d,
    generate_dense_database_3d,
    generate_gowalla,
    generate_nh_64,
    generate_random_database_2d,
    generate_spitz,
)
from ers.schemes.dependent.quad_brc_data_dependent import QuadBRCDataDependent, QuadBRCDataDependentRecords
from ers.schemes.dependent.quad_src_data_dependent import QuadSRCDataDependent, QuadSRCDataDependentRecords
from ers.schemes.dependent.range_brc_data_dependent import RangeBRCDataDependent, RangeBRCDataDependentRecords
from ers.schemes.dependent.tdag_src_data_dependent import TdagSRCDataDependent, TdagSRCDataDependentRecords
from ers.schemes.hilbert.dependent.quad_brc_hilbert_data_dependent import QuadBRCHilbertDataDependent, QuadBRCHilbertDataDependentRecords
from ers.schemes.hilbert.dependent.quad_src_hilbert_data_dependent import QuadSRCHilbertDataDependent, QuadSRCHilbertDataDependentRecords
from ers.schemes.hilbert.dependent.range_brc_hilbert_data_dependent import RangeBRCHilbertDataDependent, RangeBRCHilbertDataDependentRecords
from ers.schemes.hilbert.dependent.tdag_src_hilbert_data_dependent import TdagSRCHilbertDataDependent, TdagSRCHilbertDataDependentRecords
from ers.schemes.hilbert.hilbert_rtree_scheme import HilbertRTreeScheme
from ers.schemes.hilbert.interactive_src_hilbert import InteractiveSRCHilbert
from ers.schemes.hilbert.linear_hilbert import LinearHilbert
from ers.schemes.hilbert.quad_brc_hilbert import QuadBRCHilbert
from ers.schemes.hilbert.quad_src_hilbert import QuadSRCHilbert
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.schemes.hilbert.tdag_src_hilbert import TdagSRCHilbert
from ers.schemes.interactive.interactive_src_native import InteractiveSRCNative
from ers.schemes.linear import Linear
from ers.schemes.quad_brc import QuadBRC
from ers.schemes.quad_src import QuadSRC
from ers.schemes.range_brc import RangeBRC
from ers.schemes.rtree_scheme import RTreeScheme
from ers.schemes.tdag_src import TdagSRC
from ers.structures.point import Point

# Data-dependent dividers can degenerate into a linear chain on clustered data
# (one point per split), making tree recursion as deep as the Hilbert domain.
sys.setrecursionlimit(1_000_000)

#############################################################################
### SCHEME REGISTRY
#############################################################################

#: CLI name -> scheme class. The single source of truth for ``--scheme`` and the
#: ``scripts/`` wrappers (which validate their argument against this mapping).
schemes = {
    "linear": Linear,
    "range_brc": RangeBRC,
    "tdag_src": TdagSRC,
    "quad_brc": QuadBRC,
    "quad_src": QuadSRC,
    "linear_hilbert": LinearHilbert,
    "range_brc_hilbert": RangeBRCHilbert,
    "tdag_src_hilbert": TdagSRCHilbert,
    "quad_brc_hilbert": QuadBRCHilbert,
    "quad_src_hilbert": QuadSRCHilbert,
    "hilbert_rtree": HilbertRTreeScheme,
    "rtree": RTreeScheme,
    "interactive_src_hilbert": InteractiveSRCHilbert,
    "interactive_src": InteractiveSRCNative,
    "range_brc_data_dependent": RangeBRCDataDependent,
    "quad_brc_data_dependent": QuadBRCDataDependent,
    "quad_src_data_dependent": QuadSRCDataDependent,
    "tdag_src_data_dependent": TdagSRCDataDependent,
    "range_brc_hilbert_data_dependent": RangeBRCHilbertDataDependent,
    "quad_brc_hilbert_data_dependent": QuadBRCHilbertDataDependent,
    "quad_src_hilbert_data_dependent": QuadSRCHilbertDataDependent,
    "tdag_src_hilbert_data_dependent": TdagSRCHilbertDataDependent,
    # Record-weighted dividers (chunks hold equally many records, not cells).
    "range_brc_data_dependent_records": RangeBRCDataDependentRecords,
    "quad_brc_data_dependent_records": QuadBRCDataDependentRecords,
    "quad_src_data_dependent_records": QuadSRCDataDependentRecords,
    "tdag_src_data_dependent_records": TdagSRCDataDependentRecords,
    "range_brc_hilbert_data_dependent_records": RangeBRCHilbertDataDependentRecords,
    "quad_brc_hilbert_data_dependent_records": QuadBRCHilbertDataDependentRecords,
    "quad_src_hilbert_data_dependent_records": QuadSRCHilbertDataDependentRecords,
    "tdag_src_hilbert_data_dependent_records": TdagSRCHilbertDataDependentRecords,
}

# Two-round schemes routed through run_interactive_benchmark instead of run_benchmark.
INTERACTIVE_SCHEMES = {"interactive_src_hilbert", "interactive_src"}

#############################################################################
### DATASETS
#############################################################################

#: Dataset names accepted by ``--dataset`` (see :mod:`ers.benchmark.util.dataset_generator`).
DATASETS = ("cali", "spitz", "gowalla", "dense_2d", "random_2d", "dense_3d", "nh_64")


def get_dataset(dataset_name: str, domain_size: int, records_limit: int):
    """
    Loads a dataset as a multi-map of :class:`Point` to records.

    :param dataset_name: One of :data:`DATASETS`.
    :param domain_size: Per-dimension bit length the real datasets are scaled to.
    :param records_limit: Maximum number of records to load.
    :return: ``(dataset, dimensions)``.
    :raises ValueError: For an unknown dataset name.
    """
    match dataset_name:
        case "cali":
            d = generate_cali(domain_size, records_limit)
            dim = 2
        case "spitz":
            d = generate_spitz(domain_size, records_limit)
            dim = 2
        case "gowalla":
            d = generate_gowalla(domain_size, records_limit)
            dim = 2
        case "dense_2d":
            d = generate_dense_database_2d(domain_size, records_limit)
            dim = 2
        case "random_2d":
            d = generate_random_database_2d(domain_size, records_limit)
            dim = 2
        case "dense_3d":
            d = generate_dense_database_3d(domain_size, records_limit)
            dim = 3
        case "nh_64":
            d = generate_nh_64()
            dim = 3
        case _:
            raise ValueError(f"Unknown dataset: {dataset_name}. Should be one of: {', '.join(DATASETS)}.")

    d = {Point(list(t)): vals for t, vals in d.items()}

    return d, dim


#############################################################################
### PARSER
#############################################################################


def parse_args() -> Namespace:
    parser = argparse.ArgumentParser(description="Benchmark a range-search scheme and write an .xlsx report under benchmarks/.")
    parser.add_argument("--scheme", required=True, choices=sorted(schemes), metavar="SCHEME", help="scheme to benchmark: " + ", ".join(sorted(schemes)))
    parser.add_argument("--dataset", required=True, choices=DATASETS, help="dataset to index")
    parser.add_argument("--domain-size", required=True, type=int, help="per-dimension bit length of the domain")
    parser.add_argument("--records-limit", required=True, type=int, help="maximum number of records to load")
    parser.add_argument("--queries-count", required=True, type=int, help="queries to run (<= 0 builds the index only)")

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    scheme = schemes[args.scheme]

    dataset, dimensions = get_dataset(args.dataset, args.domain_size, args.records_limit)

    print(
        f"************************************************************\n"
        f"* Running Benchmark:\n"
        f"*     > Scheme: {args.scheme}\n"
        f"*     > Dataset name: {args.dataset}, Dimensions: {dimensions}\n"
        f"*     > Dataset domain_size: {args.domain_size}\n"
        f"*     > Records limit: {args.records_limit}\n"
        f"*     > Queries count: {args.queries_count}\n"
        f"************************************************************\n"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"./benchmarks/{args.scheme}_{args.dataset}_{dimensions}_{args.domain_size}_{args.records_limit}_{args.queries_count}_{timestamp}.xlsx"
    if args.scheme in INTERACTIVE_SCHEMES:
        run_interactive_benchmark(report_name, scheme, dimensions, dataset, args.queries_count, args.domain_size)
    else:
        run_benchmark(report_name, scheme, dimensions, dataset, args.queries_count, args.domain_size)
