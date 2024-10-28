##
## Copyright 2024 Alin-Petru Rosu and Evangelia Anna Markatou
##
## Licensed under the Apache License, Version 2.0 (the "License");
## you may not use this file except in compliance with the License.
## You may obtain a copy of the License at
##
##    http://www.apache.org/licenses/LICENSE-2.0
##
## Unless required by applicable law or agreed to in writing, software
## distributed under the License is distributed on an "AS IS" BASIS,
## WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
## See the License for the specific language governing permissions and
## limitations under the License.
##

import multiprocessing
import random
import string
import threading
import time
from typing import Dict, List

import tqdm

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.rect import Rect
from extensions.schemes.hilbert.hilbert import Hilbert
from extensions.schemes.hilbert.interval_division import PerimeterTraversalDivision, MinMaxDivision


def fill_space_plaintext_mm(space: Rect, file_size: int) -> Dict[Point, List[bytes]]:
    plaintext_mm = {}
    for y in range(space.start.y, space.end.y):
        for x in range(space.start.x, space.end.x):
            k = Point(x, y)
            c = ''.join(random.choices(string.ascii_lowercase, k=file_size)).encode('utf-8')
            plaintext_mm.update({k: [c]})
    return plaintext_mm


def generate_all_queries(space: Rect) -> List[Rect]:
    queries = []

    for x1 in range(space.start.x, space.end.x):
        for y1 in range(space.start.y, space.end.y):
            for x2 in range(x1 + 1, space.end.x + 1):
                for y2 in range(y1 + 1, space.end.y + 1):
                    queries.append(Rect(Point(x1, y1), Point(x2, y2)))

    return queries


def analyse_performance(hc, key, space_rect, job_remaining, query_rect):
    start = time.time()
    search_tokens = hc.trapdoor(key, query_rect, PerimeterTraversalDivision())
    encrypted_results = hc.search(search_tokens)
    true_positive_results = hc.resolve(key, encrypted_results)
    end = time.time()

    tp_time = end - start

    start = time.time()
    search_tokens = hc.trapdoor(key, query_rect, MinMaxDivision())
    encrypted_results = hc.search(search_tokens)
    true_false_positive_results = hc.resolve(key, encrypted_results)
    end = time.time()

    p_time = end - start

    job_remaining.value += 1

    return tp_time, p_time, len(true_positive_results) * 1.0 / len(true_false_positive_results)


def value_printer(shared_value, out_of, stop_event):
    while not stop_event.is_set():
        print(f"{time.time()} - Query progress: {shared_value.value}/{out_of}")
        time.sleep(3)


def compute_error():
    # VARIABLES
    SEC_PARAM = 16
    MIN_X = 0  # inclusive
    MIN_Y = 0
    FILE_SIZE = 1000
    MAX_SPACE_SIZE = 3

    results = []

    with multiprocessing.Manager() as manager:
        for i in tqdm.tqdm(range(1, MAX_SPACE_SIZE + 1), desc="Space Loop Progress"):
            MAX_X = 2 ** i
            MAX_Y = 2 ** i

            space_start = Point(MIN_X, MIN_Y)
            space_end = Point(MAX_X - 1, MAX_Y - 1)
            space_rect = Rect(space_start, space_end)

            plaintext_mm = fill_space_plaintext_mm(space_rect, FILE_SIZE)

            # HILBERT INIT
            hc = Hilbert(EMMEngine(MAX_X, MAX_Y))
            key = hc.setup(SEC_PARAM)
            hc.build_index(key, plaintext_mm)

            queries = generate_all_queries(space_rect)

            # Use multiprocessing.Manager to create a shared job_remaining value
            job_remaining = manager.Value('i', 0)
            args = [(hc, key, space_rect, job_remaining, query) for query in queries]

            # Start the daemon thread for printing progress
            stop_event = threading.Event()
            printer_thread = threading.Thread(target=value_printer, args=(job_remaining, len(queries), stop_event),
                                              daemon=True)
            printer_thread.start()

            # Use multiprocessing.Pool for processing
            with multiprocessing.Pool() as pool:
                results.extend(pool.starmap(analyse_performance, args))

            # Stop the daemon thread after pool processing is done
            stop_event.set()
            printer_thread.join()

    tp_times, p_times, precisions = zip(*results)

    print(f"Aggregated TP time: {sum(tp_times) / len(tp_times)}")
    print(f"Aggregated P time: {sum(p_times) / len(p_times)}")
    print(f"Aggregated precisions: {sum(precisions) / len(precisions)}")


if __name__ == "__main__":
    compute_error()
