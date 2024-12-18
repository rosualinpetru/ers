import matplotlib.pyplot as plt
import numpy as np

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from ers.structures.rect import Rect
from ers.util.serialization import BytesToObject
from extensions.schemes.hilbert.linear import LinearHilbert
from extensions.util.dataset_generator import generate_dense_database_2d
from extensions.util.query_generator import generate_random_query_2d

if __name__ == "__main__":
    # VARIABLES
    SEC_PARAM = 16

    SCHEME = LinearHilbert
    MERGE_GAP_TOLERANCE = 1
    SCALING_PERCENTAGE = 0

    DIMENSION_SIZE = 3

    plaintext_mm = generate_dense_database_2d(DIMENSION_SIZE)
    plaintext_mm = {Point(*t): plaintext_mm[t] for t in plaintext_mm}

    # HILBERT INIT
    hc = SCHEME(EMMEngine(2 ** DIMENSION_SIZE, 2 ** DIMENSION_SIZE))
    key = hc.setup(SEC_PARAM)
    hc.build_index(key, plaintext_mm)

    (c1, c2) = generate_random_query_2d(2 ** DIMENSION_SIZE, 2 ** DIMENSION_SIZE)
    (query_start, query_end) = (Point(*c1), Point(*c2))

    search_tokens = hc.trapdoor(key, query_start, query_end, MERGE_GAP_TOLERANCE, SCALING_PERCENTAGE)

    encrypted_results = hc.search(search_tokens)
    resolved_results = hc.resolve(key, encrypted_results)

    hc.trapdoor(key, query_start, query_end, 0, 0)

    num_points = 2 ** (hc.dimension * hc.edge_bits)
    hilbert_points = np.array([hc.hc.point_from_distance(i) for i in range(num_points)])

    plt.figure(figsize=(256, 256))


    def point_color(p: Point):
        q = Rect(query_start, Point(query_end.x + 1, query_end.y + 1))
        if q.contains_point(p):
            if resolved_results.isdisjoint(plaintext_mm[p]):
                return "orange"
            else:
                return "green"
        else:
            if resolved_results.isdisjoint(plaintext_mm[p]):
                return "blue"
            else:
                return "red"


    for idx, (x, y) in enumerate(hilbert_points):
        p = Point(x, y)

        color = point_color(p)

        plt.scatter(p.x, p.y, color=color)
        plt.text(p.x + 0.1, p.y + 0.1, '\n'.join([BytesToObject(s).__str__() for s in plaintext_mm[p]]), fontsize=14, color=color)
        plt.text(x - 0.2, y - 0.2, str(idx), fontsize=14, color=color)

        if idx == num_points - 1:
            continue

        (next_x, next_y) = hc.hc.point_from_distance(idx + 1)

        next_color = point_color(Point(next_x, next_y))

        segment_color = color
        if next_color == "orange":
            segment_color = color
        if color == "orange":
            segment_color = next_color
        if next_color == "green":
            segment_color = color
        if color == "green":
            segment_color = next_color

        plt.plot([x, next_x], [y, next_y], color=segment_color)


    def plot_rect(p1: Point, p2: Point, colour: str, label: str):
        x1 = p1.x - 0.1
        y1 = p1.y - 0.1

        x2 = p2.x + 0.1
        y2 = p2.y + 0.1

        plt.fill([x1, x2, x2, x1], [y1, y1, y2, y2], color=colour, alpha=0.1, label=label)


    plot_rect(Point(0, 0), Point(2 ** DIMENSION_SIZE - 1, 2 ** DIMENSION_SIZE - 1), "yellow", "Search Space")
    plot_rect(query_start, query_end, "green", "Query")

    plt.title(f"Hilbert Curve")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(False)
    plt.show()
