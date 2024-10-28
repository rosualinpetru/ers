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

import random
import string
from typing import Dict, List, Set

import matplotlib.pyplot as plt
import numpy as np
from hilbertcurve.hilbertcurve import HilbertCurve

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.rect import Rect
from extensions.schemes.hilbert.hilbert import Hilbert
from extensions.schemes.hilbert.interval_division import PerimeterTraversalDivision


def random_plaintext_mm(number_of_files: int, rect: Rect, file_size: int) -> Dict[Point, List[bytes]]:
    plaintext_mm = {}
    for i in range(number_of_files):
        x = random.randint(rect.start.x, rect.end.x)
        y = random.randint(rect.start.y, rect.end.y)
        k = Point(x, y)
        c = ''.join(random.choices(string.ascii_lowercase, k=file_size)).encode('utf-8')

        if k in plaintext_mm:
            l = plaintext_mm.get(k)
            l.append(c)
            plaintext_mm.update({k: l})
        else:
            plaintext_mm.update({k: [c]})

    return plaintext_mm


def plot_query(iterations: int, hc: HilbertCurve, space: Rect, query: Rect, plaintext_mm: Dict[Point, List[bytes]],
               query_result: Set[bytes]):
    num_points = 2 ** (2 * iterations)
    hilbert_points = np.array([hc.point_from_distance(i) for i in range(num_points)])

    plt.figure(figsize=(12, 12))

    plt.plot(hilbert_points[:, 0], hilbert_points[:, 1], color="blue")

    for idx, (x, y) in enumerate(hilbert_points):
        plt.text(x - 0.3, y - 0.2, str(idx), fontsize=6, color="blue")

    for p in plaintext_mm.keys():
        files = plaintext_mm.get(p)

        if query_result.isdisjoint(files):
            plt.scatter(p.x, p.y, color="red")
            plt.text(p.x + 0.1, p.y + 0.1, '\n'.join([s.decode('utf-8') for s in files]), fontsize=8)
        else:
            plt.scatter(p.x, p.y, color="green")
            for i, c in enumerate(files):
                if c in query_result:
                    label_color = "green"
                else:
                    label_color = "black"
                plt.text(p.x + 0.1, p.y + 0.1 + i * 0.2, c.decode('utf-8'), fontsize=8, color=label_color)

    def plot_rect(rect: Rect, color: str, label: str):
        x1 = rect.start.x - 0.1
        y1 = rect.start.y - 0.1

        x2 = rect.end.x + 0.1
        y2 = rect.end.y + 0.1

        plt.fill([x1, x2, x2, x1], [y1, y1, y2, y2], color=color, alpha=0.1, label=label)

    plot_rect(space, "yellow", "Search Space")
    plot_rect(query, "green", "Query")

    plt.title(f"Hilbert Curve")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_program():
    # VARIABLES
    SEC_PARAM = 16

    MIN_X = 0  # inclusive
    MIN_Y = 0

    MAX_X = 8  # exclusive
    MAX_Y = 8

    FILE_SIZE = 5
    NUMBER_OF_FILES = 50

    # PLAINTEXT
    space_start = Point(MIN_X, MIN_Y)
    space_end = Point(MAX_X - 1, MAX_Y - 1)
    space_rect = Rect(space_start, space_end)

    plaintext_mm = random_plaintext_mm(NUMBER_OF_FILES, space_rect, FILE_SIZE)

    # HILBERT INIT
    hc = Hilbert(EMMEngine(MAX_X, MAX_Y))
    key = hc.setup(SEC_PARAM)
    hc.build_index(key, plaintext_mm)

    # HILBERT QUERY
    while True:
        query_start = Point(random.randint(space_start.x, space_end.x), random.randint(space_start.x, space_end.x))
        query_end = Point(random.randint(space_start.x, space_end.x), random.randint(space_start.x, space_end.x))

        if query_start < query_end:
            break

    query_rect = Rect(query_start, query_end)

    search_tokens = hc.trapdoor(key, query_rect, PerimeterTraversalDivision())
    encrypted_results = hc.search(search_tokens)
    resolved_results = hc.resolve(key, encrypted_results)

    print("Search Space:" + space_rect.__str__())
    print("Query Space:" + query_rect.__str__())
    print("Plaintext: " + plaintext_mm.__str__())
    print("Trapdoors: " + search_tokens.__str__())
    print("E(Result): " + encrypted_results.__str__())
    print("Result: " + resolved_results.__str__())

    plot_query(hc.iterations, hc.hc, space_rect, query_rect, plaintext_mm, resolved_results)


if __name__ == "__main__":
    plot_program()
