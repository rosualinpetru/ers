import argparse
from argparse import Namespace
from datetime import datetime

from ers.benchmark.benchmark import run_benchmark
from ers.benchmark.util.dataset_generator import generate_cali, generate_spitz, generate_gowalla, generate_dense_database_2d, generate_nh_64, generate_random_database_2d, generate_dense_database_3d
from ers.schemes.dependent.quad_brc_data_dependent import QuadBRCDataDependent
from ers.schemes.dependent.quad_src_data_dependent import QuadSRCDataDependent
from ers.schemes.dependent.range_brc_data_dependent import RangeBRCDataDependent
from ers.schemes.hilbert.dependent.quad_brc_hilbert_data_dependent import QuadBRCHilbertDataDependent
from ers.schemes.hilbert.dependent.quad_src_hilbert_data_dependent import QuadSRCHilbertDataDependent
from ers.schemes.hilbert.dependent.range_brc_hilbert_data_dependent import RangeBRCHilbertDataDependent
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
from ers.structures.point import Point

#############################################################################
### SCHEME DICTS
#############################################################################

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
    "range_brc_data_dependent": RangeBRCDataDependent,
    "quad_brc_data_dependent": QuadBRCDataDependent,
    "quad_src_data_dependent": QuadSRCDataDependent,
    "range_brc_hilbert_data_dependent": RangeBRCHilbertDataDependent,
    "quad_brc_hilbert_data_dependent": QuadBRCHilbertDataDependent,
    "quad_src_hilbert_data_dependent": QuadSRCHilbertDataDependent,
}

#############################################################################
### DATASETS DICTS
#############################################################################

def get_dataset(dataset_name: str, domain_size: int, records_limit: int):
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
            raise ValueError(f"Unknown 2D dataset: {dataset}. Should be: cali, spitz, gowalla, dense_2d, random_2d.")

    d = {Point(list(t)): d[t] for t in d}

    return d, dim

#############################################################################
### PARSER
#############################################################################

def parse_args() -> Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scheme",
        required=True,
        type=str,
        help="Mandatory scheme argument"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=str,
        help="Mandatory dataset name argument"
    )
    parser.add_argument(
        "--domain-size",
        required=True,
        type=int,
        help="Mandatory dataset dimension bits argument"
    )
    parser.add_argument(
        "--records-limit",
        required=True,
        type=int,
        help="Mandatory records limit argument"
    )
    parser.add_argument(
        "--queries-count",
        required=True,
        type=int,
        help="Mandatory queries count argument"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    scheme = schemes[args.scheme]

    dataset, dimensions = get_dataset(args.dataset, args.domain_size, args.records_limit)

    print(f"************************************************************\n"
          f"* Running Benchmark:\n"
          f"*     > Scheme: {args.scheme}\n"
          f"*     > Dataset name: {args.dataset}, Dimensions: {dimensions}\n"
          f"*     > Dataset domain_size: {args.domain_size}\n"
          f"*     > Records limit: {args.records_limit}\n"
          f"*     > Queries count: {args.queries_count}\n"
          f"************************************************************\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"./benchmarks/{args.scheme}_{args.dataset}_{dimensions}_{args.domain_size}_{args.records_limit}_{args.queries_count}_{timestamp}.xlsx"
    run_benchmark(report_name, scheme, dimensions, dataset, args.queries_count, args.domain_size)
