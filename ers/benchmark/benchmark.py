import math
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from typing import Dict

from tqdm import tqdm

from ers.benchmark.util.query_generator import generate_bucket_query_2d, generate_bucket_query_3d
from ers.benchmark.util.xlsx_util import XLSXUtil
from ers.schemes.common.emm import EMMEngine
from ers.schemes.hilbert.linear_hilbert import LinearHilbert
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.schemes.hilbert.tdag_src_hilbert import TdagSRCHilbert
from ers.schemes.linear import Linear
from ers.schemes.quad_brc import QuadBRC
from ers.schemes.quad_src import QuadSRC
from ers.schemes.range_brc import RangeBRC
from ers.schemes.tdag_src import TdagSRC
from ers.structures.hyperrange import HyperRange

BUCK_SIZE = 10


def compute_precision(scheme):
    if isinstance(scheme, Linear):
        return False

    if isinstance(scheme, QuadBRC):
        return False

    if isinstance(scheme, RangeBRC):
        return False

    if isinstance(scheme, QuadSRC):
        return True

    if isinstance(scheme, TdagSRC):
        return True

    if isinstance(scheme, LinearHilbert):
        return False

    if isinstance(scheme, RangeBRCHilbert):
        return False

    if isinstance(scheme, TdagSRCHilbert):
        return True

    return True


def generate_query_bucks(queries_count: int, dimensions: int, domain_size: int) -> Dict[int, set]:
    bound = 2 ** domain_size

    ten_bucks = defaultdict(set)
    i = 0

    for _ in range(queries_count):
        if dimensions == 2:
            c1, c2 = generate_bucket_query_2d(bound, bound, i, BUCK_SIZE)
        elif dimensions == 3:
            c1, c2 = generate_bucket_query_3d(bound, bound, bound, i, BUCK_SIZE)
        else:
            break

        ten_bucks[i * BUCK_SIZE].add(HyperRange.from_coords(list(c1), list(c2)))
        i = (i + 1) % BUCK_SIZE

    return dict(ten_bucks)


def run_query(target_bucket, query, scheme, key, dataset):
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
        true_positives = set().union(*(
            dataset.get(p, set())
            for p in query.points()
        ))

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


def run_benchmark(report_name, scheme_constructor, dimensions, dataset, queries_count, domain_size):
    xlsx_util = XLSXUtil(report_name)

    #############################################################################
    ### Building index
    #############################################################################
    print("Building index...")
    scheme = scheme_constructor(EMMEngine(dimensions * [domain_size], dimensions))
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
    ten_bucks = generate_query_bucks(queries_count, dimensions, domain_size)

    with ProcessPoolExecutor() as executor:
        tasks = []
        for target_bucket in range(0, 99, BUCK_SIZE):
            for q in ten_bucks[target_bucket]:
                tasks.append((target_bucket, q, scheme, key, dataset))

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
