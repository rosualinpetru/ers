import matplotlib.pyplot as plt
import numpy as np

from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.linear_hilbert import LinearHilbert2D
from ers.util.serialization import BytesToObject
from ers.structures.hyperrect import HyperRect
from ers.structures.pointnd import PointND
from ers.util.generator.dataset_generator import generate_dense_database_2d
from ers.util.generator.query_generator import generate_random_query_2d

if __name__ == "__main__":
    # VARIABLES
    SEC_PARAM = 16

    SCHEME = LinearHilbert2D
    MERGE_GAP_TOLERANCE = 1
    SCALING_PERCENTAGE = 0

    DIMENSION_SIZE = 3

    plaintext_mm_raw = generate_dense_database_2d(DIMENSION_SIZE, 1000000)
    plaintext_mm = {PointND(list(t)): plaintext_mm_raw[t] for t in plaintext_mm_raw}

    # HILBERT INIT
    hc = SCHEME(EMMEngine([2 ** DIMENSION_SIZE, 2 ** DIMENSION_SIZE]))
    key = hc.setup(SEC_PARAM)
    hc.build_index(key, plaintext_mm)

    (c1, c2) = generate_random_query_2d(2 ** DIMENSION_SIZE, 2 ** DIMENSION_SIZE)
    query = HyperRect.from_coords(list(c1), list(c2))

    search_tokens = hc.trapdoor(key, query, MERGE_GAP_TOLERANCE)

    encrypted_results = hc.search(search_tokens)
    resolved_results = hc.resolve(key, encrypted_results)

    num_points = 2 ** (hc.dimensions * hc.order)
    hilbert_points = np.array([hc.hc.point_from_distance(i) for i in range(num_points)])

    plt.figure(figsize=(256, 256))


    def point_color(point: PointND):
        if query.contains_point(point):
            if resolved_results.isdisjoint(plaintext_mm[point]):
                return "orange"
            else:
                return "green"
        else:
            if resolved_results.isdisjoint(plaintext_mm[point]):
                return "blue"
            else:
                return "red"


    for idx, p in enumerate(hilbert_points):
        x = p[0]
        y = p[1]

        color = point_color(p)

        plt.scatter(x, y, color=color)
        plt.text(x + 0.1, y + 0.1, '\n'.join([BytesToObject(s).__str__() for s in plaintext_mm[p]]), fontsize=14, color=color)
        plt.text(x - 0.2, y - 0.2, str(idx), fontsize=14, color=color)

        if idx == num_points - 1:
            continue

        next_point = hc.hc.point_from_distance(idx + 1)

        next_color = point_color(next_point)

        segment_color = color
        if next_color == "orange":
            segment_color = color
        if color == "orange":
            segment_color = next_color
        if next_color == "green":
            segment_color = color
        if color == "green":
            segment_color = next_color

        plt.plot([x, next_point[0]], [y, next_point[1]], color=segment_color)


    def plot_rect(q: HyperRect, colour: str, label: str):
        x1 = q.start[0] - 0.1
        y1 = q.start[1] - 0.1

        x2 = q.end[0] + 0.1
        y2 = q.end[1] + 0.1

        plt.fill([x1, x2, x2, x1], [y1, y1, y2, y2], color=colour, alpha=0.1, label=label)


    plot_rect(HyperRect(PointND([0, 0]), PointND([2 ** DIMENSION_SIZE - 1, 2 ** DIMENSION_SIZE - 1])), "yellow", "Search Space")
    plot_rect(query, "green", "Query")

    plt.title(f"Hilbert Curve")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(False)
    plt.show()
