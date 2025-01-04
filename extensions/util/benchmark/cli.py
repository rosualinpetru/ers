import argparse
from argparse import Namespace
from datetime import datetime

from ers.schemes.linear import Linear, Linear3D
from ers.schemes.qdag_src import QdagSRC
from ers.schemes.qdag_src_3d import QdagSRC3D
from ers.schemes.quad_brc import QuadBRC
from ers.schemes.quad_brc_3d import QuadBRC3D
from ers.schemes.range_brc import RangeBRC
from ers.schemes.range_brc_3d import RangeBRC3D
from ers.schemes.tdag_src import TdagSRC
from ers.schemes.tdag_src_3d import TdagSRC3D
from ers.structures.point import Point
from ers.structures.point_3d import Point3D
from extensions.schemes.hilbert.linear import LinearHilbert
from extensions.schemes.hilbert.range_brc import RangeBRCHilbert
from extensions.schemes.hilbert.tdag_src import TdagSRCHilbert
from extensions.util.benchmark.benchmark import run_benchmark
from extensions.util.generator.dataset_generator import generate_cali, generate_spitz, generate_gowalla, generate_dense_database_2d, generate_nh_64, generate_random_database_2d

#############################################################################
### SCHEME DICTS
#############################################################################

schemes_2d = {
    "linear": Linear,
    "range_brc": RangeBRC,
    "qdag_src": QdagSRC,
    "quad_brc": QuadBRC,
    "tdag_src": TdagSRC,

    "linear_hilbert": LinearHilbert,
    "range_brc_hilbert": RangeBRCHilbert,
    "tdag_src_hilbert": TdagSRCHilbert
}

schemes_3d = {
    "linear_3d": Linear3D,
    "range_brc_3d": RangeBRC3D,
    "qdag_src_3d": QdagSRC3D,
    "quad_brc_3d": QuadBRC3D,
    "tdag_src_3d": TdagSRC3D
}

schemes_all = {**schemes_2d, **schemes_3d}


#############################################################################
### DATASETS DICTS
#############################################################################

def get_dataset_2d(dataset_name: str, dimension_bits: int, records_limit: int):
    match dataset_name:
        case "cali":
            dataset = generate_cali(dimension_bits, records_limit)
        case "spitz":
            dataset = generate_spitz(dimension_bits, records_limit)
        case "gowalla":
            dataset = generate_gowalla(dimension_bits, records_limit)
        case "dense_2d":
            dataset = generate_dense_database_2d(dimension_bits, records_limit)
        case "random_2d":
            dataset = generate_random_database_2d(dimension_bits, records_limit)
        case _:
            raise ValueError(f"Unknown 2D dataset: {dataset_name}. Should be: cali, spitz, gowalla, dense_2d, random_2d.")

    dataset = {Point(*t): dataset[t] for t in dataset}

    return dataset


def get_dataset_3d(dataset_name: str, dimension_bits: int, records_limit: int):
    match dataset_name:
        case "nh_64":
            dataset = generate_nh_64()
        case _:
            raise ValueError(f"Unknown 3D dataset: {dataset_name}. Should be: nh_64.")

    dataset = {Point3D(*t): dataset[t] for t in dataset}

    return dataset


def get_dataset(dimensions: int, dataset_name: str, dimension_bits: int, records_limit: int):
    if dimensions == 2:
        return get_dataset_2d(dataset_name, dimension_bits, records_limit)
    elif dimensions == 3:
        return get_dataset_3d(dataset_name, dimension_bits, records_limit)

    raise ValueError(f"Unhandled dimensions: {dimensions}")


#############################################################################
### DIMENSIONS
#############################################################################

def get_dimensions(scheme: str) -> int:
    if scheme in schemes_2d.values():
        return 2

    if scheme in schemes_3d.values():
        return 3

    raise ValueError(f"Unknown scheme: {scheme}")


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
        "--dataset-name",
        required=True,
        type=str,
        help="Mandatory dataset name argument"
    )
    parser.add_argument(
        "--dataset-dimension-bits",
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

    scheme = schemes_all[args.scheme]

    dimensions = get_dimensions(scheme)

    dataset = get_dataset(dimensions, args.dataset_name, args.dataset_dimension_bits, args.records_limit)

    print(f"************************************************************\n"
          f"* Running Benchmark:\n"
          f"*     > Scheme: {args.scheme}\n"
          f"*     > Dataset name: {args.dataset_name}, Dimensions: {dimensions}\n"
          f"*     > Dataset dimension_bits: {args.dataset_dimension_bits}\n"
          f"*     > Records limit: {args.records_limit}\n"
          f"*     > Queries count: {args.queries_count}\n"
          f"************************************************************\n")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_name = f"./benchmarks/{args.scheme}_{args.dataset_name}_{dimensions}_{args.dataset_dimension_bits}_{args.records_limit}_{args.queries_count}_{timestamp}.xlsx"
    run_benchmark(report_name, scheme, dimensions, dataset, args.queries_count, args.dataset_dimension_bits)
