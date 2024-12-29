import argparse
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

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
from extensions.util.benchmark.xlsx_util import XLSXUtil
from extensions.schemes.hilbert.linear import LinearHilbert
from extensions.schemes.hilbert.range_brc import RangeBRCHilbert
from extensions.schemes.hilbert.tdag_src import TdagSRCHilbert
from extensions.util.generator.dataset_generator import generate_cali, generate_spitz, generate_gowalla, generate_dense_database_2d, generate_nh_64, generate_random_database_2d
from extensions.util.generator.query_generator import generate_bucket_query_2d, generate_bucket_query_3d

BUCK_SIZE = 10

def generate_query_10_bucks(queries_count: int, dimensions: int, dataset_dimension_bits: int):
    bound = 2 ** dataset_dimension_bits

    ten_bucks = defaultdict(list)
    i = 0
    if dimensions == 2:
        for _ in range(queries_count):
            c1, c2 = generate_bucket_query_2d(bound, bound, i, BUCK_SIZE)
            p1, p2 = Point(*c1), Point(*c2)
            ten_bucks[i * BUCK_SIZE].append((p1, p2))
            i = (i + 1) % BUCK_SIZE

    elif dimensions == 3:
        for _ in range(queries_count):
            c1, c2 = generate_bucket_query_3d(bound, bound, bound, i, BUCK_SIZE)
            p1, p2 = Point3D(*c1), Point3D(*c2)
            ten_bucks[i * BUCK_SIZE].append((p1, p2))
            i = (i + 1) % BUCK_SIZE

    return ten_bucks

def run_query(scheme, key, p1, p2, target_bucket):
    t0 = time.time_ns()
    trapdoors = scheme.trapdoor(key, p1, p2)
    t1 = time.time_ns()

    trapdoor_time = t1 - t0

    if isinstance(trapdoors, list):
        trapdoor_size = sum(sys.getsizeof(r) for r in trapdoors)
    else:
        trapdoor_size = sys.getsizeof(trapdoors)

    t0 = time.time_ns()
    results = scheme.search(trapdoors)
    t1 = time.time_ns()

    search_time = t1 - t0

    t0 = time.time_ns()
    scheme.resolve(key, results)
    t1 = time.time_ns()

    resolve_time = t1 - t0

    return  {
        "target_bucket": target_bucket,
        "trapdoor_time": trapdoor_time,
        "trapdoor_size": trapdoor_size,
        "search_time": search_time,
        "resolve_time": resolve_time,
    }

def run_benchmark(report_name, scheme_constructor, dimensions, dataset, queries_count, dataset_dimension_bits):
    bound = 2 ** dataset_dimension_bits
    xlsx_util = XLSXUtil(report_name)

    #############################################################################
    ### Building index
    #############################################################################
    print("Building index...")
    scheme = scheme_constructor(EMMEngine(bound, bound))
    key = scheme.setup(16)

    t0 = time.time_ns()
    scheme.build_index(key, dataset)
    t1 = time.time_ns()

    index_build_time = t1 - t0
    xlsx_util.write_to_page("index_time", [index_build_time])

    encrypted_database_size = sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in scheme.encrypted_db.items())
    xlsx_util.write_to_page("index_size", [encrypted_database_size])

    #############################################################################
    ### Running Queries
    #############################################################################
    if queries_count <= 0:
        print("Skipping running queries...")
        xlsx_util.close()
        return

    ### Metrics maps
    trapdoor_time_map = defaultdict(list)
    trapdoor_size_map = defaultdict(list)

    search_time_map = defaultdict(list)
    resolve_time_map = defaultdict(list)

    ### Queries
    ten_bucks = generate_query_10_bucks(queries_count, dimensions, dataset_dimension_bits)

    with ThreadPoolExecutor() as executor:
        bucket_results = []

        futures = []
        for target_bucket in range(0, 99, BUCK_SIZE):
            for (p1, p2) in ten_bucks[target_bucket]:
                futures.append(executor.submit(run_query, scheme, key, p1, p2, target_bucket))

        for future in tqdm(as_completed(futures), total=len(futures), desc="Running queries"):
            res = future.result()
            bucket_results.append(res)

        for result in bucket_results:
            query_gen_time_results[tb].append(trapdoor_time)
            query_size_results[tb].append(total_token_size)
            server_handling_time_results[tb].append(handling_time)
            storage_results[tb].append(storage_len)
            decryption_results[tb].append(decryption_time)

    metrics_util.write_values("Page1", [1, 2, 3, 4, 5])
    metrics_util.write_key_values("Page2", {"Accuracy": 0.95, "Loss": 0.1})
    metrics_util.write_values("Page3", ["A", "B", "C", "D"])



