import math
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Dict

from tqdm import tqdm

from ers.schemes.common.emm import EMMEngine
from ers.schemes.hilbert.linear_hilbert import LinearHilbert2D
from ers.schemes.linear import Linear3D, Linear2D
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
from ers.util.benchmark.xlsx_util import XLSXUtil
from ers.util.generator.query_generator import generate_bucket_query_2d, generate_bucket_query_3d
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.schemes.hilbert.tdag_src_hilbert import TdagSRCHilbert

BUCK_SIZE = 10


def compute_precision(scheme):
    if isinstance(scheme, Linear2D) or isinstance(scheme, Linear3D):
        return False

    if isinstance(scheme, QuadBRC) or isinstance(scheme, QuadBRC3D):
        return False

    if isinstance(scheme, RangeBRC) or isinstance(scheme, RangeBRC3D):
        return False

    if isinstance(scheme, QdagSRC) or isinstance(scheme, QdagSRC3D):
        return True

    if isinstance(scheme, TdagSRC) or isinstance(scheme, TdagSRC3D):
        return True

    if isinstance(scheme, LinearHilbert2D):
        return False

    if isinstance(scheme, RangeBRCHilbert):
        return False

    if isinstance(scheme, TdagSRCHilbert):
        return True

    return True


def generate_query_bucks(queries_count: int, dimensions: int, dataset_dimension_bits: int) -> Dict[int, set]:
    bound = 2 ** dataset_dimension_bits

    ten_bucks = defaultdict(set)
    i = 0
    if dimensions == 2:
        for _ in range(queries_count):
            c1, c2 = generate_bucket_query_2d(bound, bound, i, BUCK_SIZE)
            p1, p2 = Point(*c1), Point(*c2)
            ten_bucks[i * BUCK_SIZE].add((p1, p2))
            i = (i + 1) % BUCK_SIZE

    elif dimensions == 3:
        for _ in range(queries_count):
            c1, c2 = generate_bucket_query_3d(bound, bound, bound, i, BUCK_SIZE)
            p1, p2 = Point3D(*c1), Point3D(*c2)
            ten_bucks[i * BUCK_SIZE].add((p1, p2))
            i = (i + 1) % BUCK_SIZE

    return dict(ten_bucks)


def run_query(target_bucket, query, scheme, key, dimensions, dataset):
    t0 = time.time_ns()
    trapdoors = scheme.trapdoor(key, query)
    t1 = time.time_ns()

    trapdoor_time = t1 - t0

    if isinstance(trapdoors, list) or isinstance(trapdoors, set):
        trapdoor_size = sum(sys.getsizeof(r) for r in trapdoors)
        trapdoor_count = len(trapdoors)
    else:
        trapdoor_size = sys.getsizeof(trapdoors)
        trapdoor_count = 1

    t0 = time.time_ns()
    encrypted_results = scheme.search(trapdoors)
    t1 = time.time_ns()

    search_time = t1 - t0
    search_count = len(encrypted_results)

    t0 = time.time_ns()
    all_positives = scheme.resolve(key, encrypted_results)
    t1 = time.time_ns()

    resolve_time = t1 - t0

    if compute_precision(scheme):
        if dimensions == 2:
            true_positives = set().union(*(
                dataset.get(Point(x, y), set())
                for x in range(p1.x, p2.x + 1)
                for y in range(p1.y, p2.y + 1)
            ))
        elif dimensions == 3:
            true_positives = set().union(*(
                dataset.get(Point3D(x, y, z), set())
                for x in range(p1.x, p2.x + 1)
                for y in range(p1.y, p2.y + 1)
                for z in range(p1.z, p2.z + 1)
            ))
        else:
            raise ValueError("Unsupported dimensions: only 2D and 3D are supported.")

        if not true_positives.issubset(all_positives):
            print("The scheme records false negatives...")
            precision = float('-inf')
        else:
            precision = len(true_positives) * 1.0 / len(all_positives) if len(all_positives) != 0 else 1
    else:
        precision = -1

    return {
        "target_bucket": target_bucket,
        "trapdoor_time": trapdoor_time,
        "trapdoor_size": trapdoor_size,
        "trapdoor_count": trapdoor_count,
        "search_time": search_time,
        "search_count": search_count,
        "resolve_time": resolve_time,
        "precision": precision
    }


def run_query_with_params(args):
    return run_query(*args)


def run_benchmark(report_name, scheme_constructor, dimensions, dataset, queries_count, dataset_dimension_bits):
    bound = 2 ** dataset_dimension_bits
    xlsx_util = XLSXUtil(report_name)

    #############################################################################
    ### Building index
    #############################################################################
    print("Building index...")
    scheme = scheme_constructor(EMMEngine(dimensions * [bound]))
    key = scheme.setup(16)

    t0 = time.time_ns()
    scheme.build_index(key, dataset)
    t1 = time.time_ns()

    index_build_time = t1 - t0
    xlsx_util.write_to_page("index_time", [index_build_time / 10 ** 9])

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
    trapdoor_count_map = defaultdict(list)

    search_time_map = defaultdict(list)
    search_count_map = defaultdict(list)

    resolve_time_map = defaultdict(list)

    precision_map = defaultdict(list)

    ### Queries
    ten_bucks = generate_query_bucks(queries_count, dimensions, dataset_dimension_bits)

    with ProcessPoolExecutor() as executor:
        tasks = []
        for target_bucket in range(0, 99, BUCK_SIZE):
            for (p1, p2) in ten_bucks[target_bucket]:
                tasks.append((target_bucket, p1, p2, scheme, key, dimensions, dataset))

        results = list(tqdm(executor.map(run_query_with_params, tasks), total=len(tasks), desc="Running queries"))

        for result in results:
            tb = result["target_bucket"]

            trapdoor_time_map[tb].append(result["trapdoor_time"])
            trapdoor_size_map[tb].append(result["trapdoor_size"])
            trapdoor_count_map[tb].append(result["trapdoor_count"])

            search_time_map[tb].append(result["search_time"])
            search_count_map[tb].append(result["search_count"])

            resolve_time_map[tb].append(result["resolve_time"])

            precision_map[tb].append(result["precision"])

    for bucket, trapdoor_times in trapdoor_time_map.items():
        xlsx_util.write_to_page("trapdoor_time", [bucket, (sum(trapdoor_times) / len(trapdoor_times)) / 10 ** 9])

    for bucket, trapdoor_sizes in trapdoor_size_map.items():
        xlsx_util.write_to_page("trapdoor_size", [bucket, math.floor(sum(trapdoor_sizes) / len(trapdoor_sizes))])

    for bucket, trapdoor_counts in trapdoor_count_map.items():
        xlsx_util.write_to_page("trapdoor_count", [bucket, math.floor(sum(trapdoor_counts) / len(trapdoor_counts))])

    for bucket, search_times in search_time_map.items():
        xlsx_util.write_to_page("search_time", [bucket, (sum(search_times) / len(search_times)) / 10 ** 9])

    for bucket, search_counts in search_count_map.items():
        xlsx_util.write_to_page("search_count", [bucket, math.floor(sum(search_counts) / len(search_counts))])

    for bucket, resolve_times in resolve_time_map.items():
        xlsx_util.write_to_page("resolve_time", [bucket, (sum(resolve_times) / len(resolve_times)) / 10 ** 9])

    for bucket, precisions in precision_map.items():
        if any(x < 0 for x in precisions):
            xlsx_util.write_to_page("precision", [bucket, min(precisions)])
        else:
            xlsx_util.write_to_page("precision", [bucket, (sum(precisions) / len(precisions))])

    xlsx_util.close()
