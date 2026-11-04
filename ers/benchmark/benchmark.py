"""
Benchmark driver for the range-search schemes.

Builds a scheme's encrypted index over a dataset, runs a batch of range queries
grouped into selectivity buckets, and records timing, size, and precision
metrics to an .xlsx report. Queries are cached on disk (``queries/``) so every
scheme sees the same workload, and executed in parallel across processes.

Caveat on timings: queries of one run execute concurrently, and several runs
are usually launched side by side, so the wall-clock metrics are
contention-affected. Token counts, result counts, precision and index size are
deterministic and load-independent.
"""

import ast
import math
import os
import pickle
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool
from typing import Dict, List

from tqdm import tqdm

from ers.benchmark.util.query_generator import generate_bucket_query_2d, generate_bucket_query_3d
from ers.benchmark.util.xlsx_util import XLSXUtil
from ers.schemes.common.emm import EMM
from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.hyperrange import HyperRange

BUCK_SIZE = 10

#: Metrics whose per-bucket averages are written as integers.
_INTEGER_METRICS = {"trapdoor_size", "trapdoor_count", "trapdoor_count_round1", "trapdoor_count_round2", "search_count"}

#: Precision sentinel for exact schemes: not measured, 1.0 by construction.
PRECISION_EXACT = -1
#: Precision sentinel for a false negative: the scheme dropped a true positive.
PRECISION_FALSE_NEGATIVE = float("-inf")


def compute_precision(scheme: EMM) -> bool:
    """
    Reports whether precision must be measured for this scheme.

    Exact schemes (``scheme.exact``: the linear scheme and every Best-Range-Cover
    scheme at merging tolerance 0) have precision 1 by construction, so the
    harness skips the true-positive enumeration and records
    :data:`PRECISION_EXACT`; lossy schemes (Single Range Cover, packed R-trees,
    interactive with an SRC second round) are measured per query.

    :param scheme: The scheme instance under benchmark.
    :return: ``True`` if the scheme can return false positives.
    """
    return not scheme.exact


def measure_precision(query: HyperRange, dataset, all_positives) -> float:
    """
    True positives divided by returned results for one query.

    :param query: The query range.
    :param dataset: The plaintext multi-map, to enumerate the true positives.
    :param all_positives: The decrypted results of the scheme.
    :return: The precision, or :data:`PRECISION_FALSE_NEGATIVE` if a true positive is missing.
    """
    true_positives = set().union(*(dataset.get(p, set()) for p in query.points()))
    if not true_positives.issubset(all_positives):
        print("The scheme records false negatives...")
        return PRECISION_FALSE_NEGATIVE
    return len(true_positives) / len(all_positives) if all_positives else 1.0


def write_bucket_averages(xlsx_util: XLSXUtil, metric_maps: Dict[str, Dict[int, List[float]]]) -> None:
    """
    Writes, per metric sheet, one row ``(bucket, average)`` per selectivity bucket.

    Integer metrics are floored; a precision bucket containing a sentinel
    (exact or false negative) records the minimum so the sentinel survives.

    :param xlsx_util: The report to write to.
    :param metric_maps: ``metric -> bucket -> [per-query values]``.
    """
    for name, buckets in metric_maps.items():
        for bucket, values in buckets.items():
            if name == "precision" and any(v < 0 for v in values):
                avg = min(values)
            else:
                avg = sum(values) / len(values)
            xlsx_util.write_to_page(name, [bucket, math.floor(avg) if name in _INTEGER_METRICS else avg])


def generate_query_bucks(queries_count: int, dimensions: int, domain_size: int) -> Dict[int, List]:
    """
    Generates (or loads from cache) range queries grouped by selectivity bucket.

    Queries are bucketed by the fraction of the domain they cover (in steps of
    ``BUCK_SIZE`` percent) so that performance can be reported per selectivity
    level. The generated set is cached under ``queries/`` and reused on later runs.

    :param queries_count: The total number of queries to generate.
    :param dimensions: The dataset dimensionality (2 or 3).
    :param domain_size: The bit-length of each dimension's domain.
    :return: A mapping from bucket key to a list of HyperRange queries.
    """
    filepath = f"queries/q_{dimensions}_{domain_size}.txt"

    if os.path.exists(filepath):
        with open(filepath, "r") as file:
            content = file.read()
            ten_bucks = ast.literal_eval(content)
            ten_bucks = {int(k): [HyperRange.from_coords(list(start), list(end)) for start, end in vs] for k, vs in ten_bucks.items()}
        return ten_bucks

    bound = 2**domain_size
    ten_bucks = defaultdict(list)
    i = 0

    for _ in range(queries_count):
        if dimensions == 2:
            c1, c2 = generate_bucket_query_2d(bound, bound, i, BUCK_SIZE)
        elif dimensions == 3:
            c1, c2 = generate_bucket_query_3d(bound, bound, bound, i, BUCK_SIZE)
        else:
            break

        ten_bucks[i * BUCK_SIZE].append(HyperRange.from_coords(list(c1), list(c2)))
        i = (i + 1) % BUCK_SIZE

    serializable_ten_bucks = {k: [(tuple(hr.start.coords()), tuple(hr.end.coords())) for hr in vs] for k, vs in ten_bucks.items()}

    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    with open(filepath, "w") as file:
        file.write(str(serializable_ten_bucks))

    return dict(ten_bucks)


def run_query(target_bucket, query, scheme, key, dataset):
    """
    Executes a single query end-to-end and measures its cost and precision.

    Times the trapdoor, search, and resolve phases; records trapdoor size/count
    and result count; and, for lossy schemes, computes precision by comparing the
    returned values against the true positives for the query.

    :param target_bucket: The selectivity bucket this query belongs to.
    :param query: The HyperRange to search.
    :param scheme: The scheme instance to query.
    :param key: The secret key for trapdoor generation and resolution.
    :param dataset: The plaintext dataset, used to compute true positives.
    :return: A dict of per-query metrics keyed by metric name.
    """
    t0 = time.perf_counter()
    trapdoors = scheme.trapdoor(key, query)
    t1 = time.perf_counter()

    trapdoor_time = t1 - t0

    trapdoor_size = sum(sys.getsizeof(r) for r in trapdoors)
    trapdoor_count = len(trapdoors)

    t0 = time.perf_counter()
    encrypted_results = scheme.search(trapdoors)
    t1 = time.perf_counter()

    search_time = t1 - t0
    search_count = len(encrypted_results)

    t0 = time.perf_counter()
    all_positives = scheme.resolve(key, encrypted_results)
    t1 = time.perf_counter()

    resolve_time = t1 - t0

    precision = measure_precision(query, dataset, all_positives) if compute_precision(scheme) else PRECISION_EXACT

    return {
        "target_bucket": target_bucket,
        "trapdoor_time": trapdoor_time,
        "trapdoor_size": trapdoor_size,
        "trapdoor_count": trapdoor_count,
        "search_time": search_time,
        "search_count": search_count,
        "resolve_time": resolve_time,
        "precision": precision,
    }


def run_query_with_params(args):
    """
    Unpacks a tuple of arguments and forwards them to :func:`run_query`.

    Used as the mapped callable for :class:`ProcessPoolExecutor`, which passes a
    single packed argument to each task.

    :param args: A tuple ``(target_bucket, query, scheme, key, dataset)``.
    :return: The per-query metrics dict from :func:`run_query`.
    """
    return run_query(*args)


def _run_queries(tasks: List[tuple]) -> List[dict]:
    """
    Runs the query tasks in a process pool, falling back to in-process
    sequential execution when the scheme cannot be shipped to the workers.

    Every task carries the scheme (with its client-side structure) and is
    pickled for the pool. Deep data-dependent trees over large domains exceed
    the pickler's recursion limit, which surfaces as a ``RecursionError`` or a
    broken pool; the fallback trades parallelism for completing the run, and
    only the (contention-affected anyway) timings are affected.

    :param tasks: ``(bucket, query, scheme, key, dataset)`` tuples.
    :return: One metrics dict per task, in task order.
    """
    try:
        with ProcessPoolExecutor() as executor:
            return list(tqdm(executor.map(run_query_with_params, tasks), total=len(tasks), desc="Running queries"))
    except (RecursionError, BrokenProcessPool, pickle.PicklingError) as e:
        print(f"Process pool unavailable ({type(e).__name__}); running the queries sequentially in this process.")
        return [run_query_with_params(t) for t in tqdm(tasks, desc="Running queries (sequential)")]


def run_benchmark(report_name, scheme_constructor, dimensions, dataset, queries_count, domain_size):
    """
    Builds a scheme's index, runs the query workload, and writes an .xlsx report.

    Measures index build time and size, then (unless ``queries_count`` is
    non-positive) runs the bucketed queries in parallel and writes per-bucket
    averages for each metric to the report.

    :param report_name: Path of the .xlsx report to produce.
    :param scheme_constructor: Callable taking an EMMEngine and returning a scheme.
    :param dimensions: The dataset dimensionality.
    :param dataset: The plaintext multi-map to index and query.
    :param queries_count: Number of queries to run (<= 0 skips the query phase).
    :param domain_size: The bit-length of each dimension's domain.
    """
    xlsx_util = XLSXUtil(report_name)

    #############################################################################
    ### Building index
    #############################################################################
    print("Building index...")
    scheme = scheme_constructor(EMMEngine(dimensions * [domain_size], dimensions))
    key = scheme.setup(16)

    t0 = time.perf_counter()
    scheme.build_index(key, dataset)
    t1 = time.perf_counter()

    index_build_time = t1 - t0
    xlsx_util.write_to_page("index_time", [index_build_time])

    encrypted_database_size = sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in scheme._require_index().items())
    xlsx_util.write_to_page("index_size", [encrypted_database_size])

    #############################################################################
    ### Running Queries
    #############################################################################
    if queries_count <= 0:
        print("Skipping running queries...")
        xlsx_util.close()
        return

    metric_maps: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))  # metric -> bucket -> [values]
    ten_bucks = generate_query_bucks(queries_count, dimensions, domain_size)

    tasks = [(target_bucket, q, scheme, key, dataset) for target_bucket in range(0, 99, BUCK_SIZE) for q in ten_bucks.get(target_bucket, [])]
    results = _run_queries(tasks)

    for result in results:
        tb = result.pop("target_bucket")
        for name, value in result.items():
            metric_maps[name][tb].append(value)

    write_bucket_averages(xlsx_util, metric_maps)
    xlsx_util.close()


def run_interactive_benchmark(report_name, scheme_constructor, dimensions, dataset, queries_count, domain_size):
    """
    Benchmark driver for the two-round interactive schemes, writing a report in
    the same sheet layout as :func:`run_benchmark` so the dashboard can compare
    them against the single-round schemes. Adds ``trapdoor_count_round1`` and
    ``trapdoor_count_round2`` sheets for the per-round token split.

    The two-round protocol carries query-dependent state between rounds, so it is
    run sequentially rather than through the process pool.
    """
    xlsx_util = XLSXUtil(report_name)

    print("Building index...")
    scheme = scheme_constructor(EMMEngine(dimensions * [domain_size], dimensions))
    key = scheme.setup(16)

    t0 = time.perf_counter()
    scheme.build_index(key, dataset)
    t1 = time.perf_counter()

    xlsx_util.write_to_page("index_time", [t1 - t0])
    # Both indices count toward the server's storage.
    xlsx_util.write_to_page("index_size", [scheme.index1_size_bytes() + scheme.index2_size_bytes()])

    if queries_count <= 0:
        print("Skipping running queries...")
        xlsx_util.close()
        return

    metric_maps: Dict[str, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))  # metric -> bucket -> [values]
    ten_bucks = generate_query_bucks(queries_count, dimensions, domain_size)

    tasks = [(tb, q) for tb in range(0, 99, BUCK_SIZE) for q in ten_bucks.get(tb, [])]
    for target_bucket, query in tqdm(tasks, desc="Running queries"):
        documents, m = scheme.query_with_metrics(key, query)
        for name in ("trapdoor_time", "search_time", "resolve_time", "trapdoor_count", "trapdoor_count_round1", "trapdoor_count_round2", "search_count"):
            metric_maps[name][target_bucket].append(m[name])
        metric_maps["precision"][target_bucket].append(measure_precision(query, dataset, documents))

    write_bucket_averages(xlsx_util, metric_maps)
    xlsx_util.close()
