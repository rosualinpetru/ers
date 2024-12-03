import multiprocessing
import time

import tqdm
from matplotlib import pyplot as plt

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.linear import Linear
from ers.schemes.range_brc import RangeBRC
from ers.schemes.tdag_src import TdagSRC
from ers.structures.point import Point
from extensions.experiments.utils import fill_space_plaintext_mm, random_query_2d
from extensions.schemes.hilbert.linear import LinearHilbert
from extensions.schemes.hilbert.range_brc import RangeBRCHilbert
from extensions.schemes.hilbert.tdag_src import TdagSRCHilbert


def analyse_performance(hc, hc_key, base, base_key, query_start, query_end):
    tp = (query_end.x - query_start.x + 1) * (query_end.y - query_start.y + 1)

    start = time.perf_counter()
    hc_results = hc.search(hc.trapdoor(hc_key, query_start, query_end, 50))
    end = time.perf_counter()
    tp_fp_hc = len(hc_results)

    hc_time = end - start


    start = time.perf_counter()
    base_results = base.search(base.trapdoor(base_key, query_start, query_end))
    end = time.perf_counter()
    tp_fp_base = len(base_results)

    base_time = end - start

    return base_time, hc_time, tp / tp_fp_base if tp_fp_base != 0 else 0,  tp / tp_fp_hc if tp_fp_hc != 0 else 0


def compute_error(hilbert_scheme, base_scheme, name):
    # VARIABLES
    SEC_PARAM = 16
    MIN_X = 0  # inclusive
    MIN_Y = 0
    MAX_SPACE_SIZE = 7
    RANDOM_EXPERIMENT_COUNT = 16

    space_sizes = []
    hc_avg_times = []
    base_avg_times = []

    for i in tqdm.tqdm(range(1, MAX_SPACE_SIZE + 1), desc=f"Space Size {name}"):
        results = []

        MAX_X = 2 ** i
        MAX_Y = 2 ** i

        space_start = Point(MIN_X, MIN_Y)
        space_end = Point(MAX_X - 1, MAX_Y - 1)

        plaintext_mm = fill_space_plaintext_mm(space_start, space_end)

        # HILBERT INIT
        hc = hilbert_scheme(EMMEngine(MAX_X, MAX_Y))
        hc_key = hc.setup(SEC_PARAM)
        hc.build_index(hc_key, plaintext_mm)

        base = base_scheme(EMMEngine(MAX_X, MAX_Y))
        base_key = base.setup(SEC_PARAM)
        base.build_index(base_key, plaintext_mm)

        queries = [random_query_2d(space_start, space_end) for _ in range(0, RANDOM_EXPERIMENT_COUNT)]

        args = [(hc, hc_key, base, base_key, start, end) for (start, end) in queries]

        with multiprocessing.Pool(16) as pool:
            results.extend(pool.starmap(analyse_performance, args))

        base_times, hc_times, base_precisions, hc_precisions  = zip(*results)
        space_sizes.append(i)
        base_avg_times.append(sum(base_times) / len(base_times))
        hc_avg_times.append(sum(hc_times) / len(hc_times))

        print(f"{name} - Space size: {i}")
        print(f"Base precision: {sum(base_precisions) / len(base_precisions)}")
        print(f"Hilbert precision: {sum(hc_precisions) / len(hc_precisions)}")

    plt.figure()
    plt.plot(space_sizes, base_avg_times, label=f"{name}")
    # Plot the cosine function
    plt.plot(space_sizes, hc_avg_times, label=f"{name}Hilbert", color="orange")
    # Add title and labels
    plt.title(f"{name}")
    plt.xlabel("Space Size (2 ** x)")
    plt.ylabel("Average time")

    plt.legend()
    plt.grid(True)
    plt.show()


if __name__ == "__main__":
    # compute_error(LinearHilbert, Linear, "Linear")
    # compute_error(RangeBRCHilbert, RangeBRC, "RangeBRC")
    compute_error(TdagSRCHilbert, TdagSRC, "TdagSRC")
