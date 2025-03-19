import matplotlib.pyplot as plt
import numpy as np

from ers.benchmark.util.dataset_generator import generate_dense_database_2d
from ers.benchmark.util.query_generator import generate_bucket_query_2d
from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.dependent.quad_brc_hilbert_data_dependent import QuadBRCHilbertDataDependent
from ers.schemes.hilbert.dependent.quad_src_hilbert_data_dependent import QuadSRCHilbertDataDependent
from ers.schemes.hilbert.dependent.range_brc_hilbert_data_dependent import RangeBRCHilbertDataDependent
from ers.schemes.hilbert.linear_hilbert import LinearHilbert
from ers.schemes.hilbert.quad_brc_hilbert import QuadBRCHilbert
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.schemes.hilbert.tdag_src_hilbert import TdagSRCHilbert
from ers.schemes.range_brc import RangeBRC
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point
from ers.util.serialization.serialization import BytesToObject

if __name__ == "__main__":
    # VARIABLES
    SEC_PARAM = 16

    SCHEME = RangeBRCHilbertDataDependent
    MERGE_GAP_TOLERANCE = 0
    SCALING_PERCENTAGE = 0

    DOMAIN_BITS = 3

    plaintext_mm_raw = generate_dense_database_2d(DOMAIN_BITS, 1000000)
    plaintext_mm = {Point(list(t)): plaintext_mm_raw[t] for t in plaintext_mm_raw}

    # HILBERT INIT
    hc = SCHEME(EMMEngine([DOMAIN_BITS, DOMAIN_BITS], 2))
    key = hc.setup(SEC_PARAM)
    hc.build_index(key, plaintext_mm)

    (c1, c2) = generate_bucket_query_2d(2 ** DOMAIN_BITS, 2 ** DOMAIN_BITS, 0, 10)
    query = HyperRange.from_coords(list(c1), list(c2))

    search_tokens = hc.trapdoor(key, query)

    encrypted_results = hc.search(search_tokens)
    resolved_results = hc.resolve(key, encrypted_results)

    num_points = 2 ** (hc.dimensions * hc.order)
    hilbert_points = np.array([hc.hc.point_from_distance(i) for i in range(num_points)])

    plt.figure(figsize=(256, 256))

    def point_color(point: Point):
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
        plt.text(x + 0.1, y + 0.1, "{"+'\n'.join([BytesToObject(s).__str__()+"}" for s in plaintext_mm[p]]), fontsize=12, color=color)
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


    def plot_rect(q: HyperRange, colour: str, label: str):
        x1 = q.start[0] - 0.1
        y1 = q.start[1] - 0.1

        x2 = q.end[0] + 0.1
        y2 = q.end[1] + 0.1

        plt.fill([x1, x2, x2, x1], [y1, y1, y2, y2], color=colour, alpha=0.1, label=label)


    plot_rect(HyperRange(Point([0, 0]), Point([2 ** DOMAIN_BITS - 1, 2 ** DOMAIN_BITS - 1])), "yellow", "Search Space")
    plot_rect(query, "green", "Query")

    plt.title(f"Hilbert Curve")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.grid(False)
    plt.show()
