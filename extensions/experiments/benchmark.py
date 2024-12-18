import argparse
import sys
import threading
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from tqdm import tqdm

from ers.schemes.common.emm import EMMEngine
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
from extensions.util.dataset_generator import generate_cali, generate_spitz, generate_gowalla, generate_dense_database_2d, generate_nh_64, generate_random_database_2d
from extensions.util.query_generator import generate_bucket_query_2d, generate_bucket_query_3d


def generate_query_10_bucks(queries_count: int, dimensions: int, database_dimension_size: int):
    bound = 2 ** database_dimension_size
    buck_size = 10

    ten_bucks = defaultdict(list)
    i = 0
    if dimensions == 2:
        for _ in range(queries_count):
            c1, c2 = generate_bucket_query_2d(bound, bound, i, buck_size)
            p1, p2 = Point(*c1), Point(*c2)
            ten_bucks[i * buck_size].append((p1, p2))
            i = (i + 1) % buck_size

    elif dimensions == 3:
        for _ in range(queries_count):
            c1, c2 = generate_bucket_query_3d(bound, bound, bound, i, buck_size)
            p1, p2 = Point3D(*c1), Point3D(*c2)
            ten_bucks[i * buck_size].append((p1, p2))
            i = (i + 1) % buck_size

    return ten_bucks


def run_benchmark(scheme_name, dimensions, scheme, queries_count, database, database_dimension_size, database_name):
    print("***************************************************************************************")
    print(
        f"Scheme: {scheme_name} Database name: {database_name}  Dimensions: {dimensions} Query count: {queries_count} Database dimension size: {database_dimension_size}")
    print("***************************************************************************************")

    bound = 2 ** database_dimension_size

    #############################################################################
    ### Building index
    #############################################################################
    s = scheme(EMMEngine(bound, bound))
    key = s.setup(16)

    t0 = time.time_ns()
    s.build_index(key, database)
    t1 = time.time_ns()
    build_index_time = t1 - t0

    encrypted_db_size = sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in s.encrypted_db.items())

    #############################################################################
    ### Building index
    #############################################################################

    query_gen_time_results = defaultdict(list)
    query_size_results = defaultdict(list)

    server_handling_time_results = defaultdict(list)
    storage_results = defaultdict(list)

    decryption_results = defaultdict(list)

    def do_query_benchmark(p1, p2, target_bucket):
        t0 = time.time_ns()
        trapdoors = s.trapdoor(key, p1, p2)
        t1 = time.time_ns()
        trapdoor_time = t1 - t0

        if isinstance(trapdoors, list):
            total_token_size = sum(sys.getsizeof(r) for r in trapdoors)
        else:
            total_token_size = sys.getsizeof(trapdoors)

        t0 = time.time_ns()
        results = s.search(trapdoors)
        t1 = time.time_ns()
        handling_time = t1 - t0

        t0 = time.time_ns()
        s.resolve(key, results)
        t1 = time.time_ns()
        decryption_time = t1 - t0

        return target_bucket, trapdoor_time, total_token_size, handling_time, len(results), decryption_time

    ten_bucks = generate_query_10_bucks(queries_count, dimensions, database_dimension_size)

    query_time_start = time.time()

    with ThreadPoolExecutor() as executor:
        bucket_results = []

        futures = []
        for target_bucket in range(0, 99, 10):
            for (p1, p2) in ten_bucks[target_bucket]:
                futures.append(executor.submit(do_query_benchmark, p1, p2, target_bucket))

        for future in tqdm(as_completed(futures), total=len(futures), desc="Running queries"):
            res = future.result()
            bucket_results.append(res)

        for (tb, trapdoor_time, total_token_size, handling_time, storage_len, decryption_time) in bucket_results:
            query_gen_time_results[tb].append(trapdoor_time)
            query_size_results[tb].append(total_token_size)
            server_handling_time_results[tb].append(handling_time)
            storage_results[tb].append(storage_len)
            decryption_results[tb].append(decryption_time)

    query_time_end = time.time()

    print("***************************************************************************************")
    print(
        f"Scheme: {scheme_name} Database name: {database_name}  Dimensions: {dimensions} Query count: {queries_count} Database dimension size: {database_dimension_size}")
    print("***************************************************************************************")
    print("Getting ", queries_count, "queries took ", query_time_end - query_time_start)

    print("IndexSizeBytes,ConstructTimeNS")
    print(f"{encrypted_db_size},{build_index_time}")
    print("* ----------------------------------------------------------------------------------- *")

    print("PercentOfDomain,Average Query Time (sec)")
    for bucket, sizes in query_gen_time_results.items():
        print(f"{bucket},{(sum(sizes) / len(sizes)) / 10 ** 9}")
    print("* ----------------------------------------------------------------------------------- *")

    print("PercentOfDomain,Average Query Size (bytes)")
    for bucket, sizes in query_size_results.items():
        print(f"{bucket},{(sum(sizes) / len(sizes))}")
    print("* ----------------------------------------------------------------------------------- *")

    print("PercentOfDomain, Average Eval Time (sec)")
    for bucket, sizes in server_handling_time_results.items():
        print(f"{bucket},{(sum(sizes) / len(sizes)) / 10 ** 9}")
    print("* ----------------------------------------------------------------------------------- *")

    print("PercentOfDomain,Average Result Count ")
    for bucket, sizes in storage_results.items():
        print(f"{bucket},{sum(sizes) / len(sizes)}")
    print("* ----------------------------------------------------------------------------------- *")

    print("PercentOfDomain,Average Result Time (sec)")
    for bucket, sizes in decryption_results.items():
        print(f"{bucket},{(sum(sizes) / len(sizes)) / 10 ** 9}")

    print("***************************************************************************************")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scheme",
        required=True,
        type=str,
        help="Mandatory scheme argument"
    )
    parser.add_argument(
        "--queries-count",
        required=True,
        type=int,
        help="Mandatory queries count argument"
    )
    parser.add_argument(
        "--dataset",
        required=True,
        type=str,
        help="Mandatory dataset argument"
    )
    parser.add_argument(
        "--dataset-dimension-size",
        required=True,
        type=int,
        help="Mandatory dataset dimension size argument"
    )
    parser.add_argument(
        "--records",
        type=int,
        help="Optional records argument for random dataset"
    )

    args = parser.parse_args()

    scheme_dict = {
        "range_brc": RangeBRC,
        "range_brc_3d": RangeBRC3D,
        "linear": Linear,
        "linear_3d": Linear3D,
        "qdag_src": QdagSRC,
        "qdag_src_3d": QdagSRC3D,
        "quad_brc": QuadBRC,
        "quad_brc_3d": QuadBRC3D,
        "tdag_src": TdagSRC,
        "tdag_src_3d": TdagSRC3D,
        "linear_hilbert": LinearHilbert,
        "range_brc_hilbert": RangeBRCHilbert,
        "tdag_src_hilbert": TdagSRCHilbert,
    }
    scheme = scheme_dict[args.scheme]

    # Should be generalised for each number of dimensions

    if "3d" in args.scheme:
        dimensions = 3
    else:
        dimensions = 2

    dataset = None

    print(dimensions)
    if dimensions == 2:
        match args.dataset:
            case "cali":
                dataset = generate_cali(args.dataset_dimension_size)
            case "spitz":
                dataset = generate_spitz(args.dataset_dimension_size)
            case "gowalla":
                dataset = generate_gowalla(args.dataset_dimension_size)
            case "dense_2d":
                dataset = generate_dense_database_2d(args.dataset_dimension_size)
            case "random_2d":
                dataset = generate_random_database_2d(args.dataset_dimension_size, args.records)
            case _:
                raise "Unknown 2D dataset. should be: cali, spitz, gowalla, dense_2d, random_2d"

        dataset = {Point(*t): dataset[t] for t in dataset}

    elif dimensions == 3:
        match args.dataset:
            case "nh_64":
                dataset = generate_nh_64()
            case _:
                raise "Unknown 3D dataset. should be: nh_64"

        dataset = {Point3D(*t): dataset[t] for t in dataset}

    if dataset is None:
        raise "Unknown dataset for the current input"

    run_benchmark(args.scheme, dimensions, scheme, args.queries_count, dataset, args.dataset_dimension_size, args.dataset)
