import matplotlib.pyplot as plt
import numpy as np

from ers.schemes.common.emm_engine import EMMEngine
from ers.structures.point import Point
from extensions.experiments.utils import fill_space_plaintext_mm, random_query_2d
from extensions.schemes.hilbert.linear import LinearHilbert

if __name__ == "__main__":
    # VARIABLES
    SEC_PARAM = 16

    MIN_X = 0  # inclusive
    MIN_Y = 0

    MAX_X = 16  # exclusive
    MAX_Y = 16

    # PLAINTEXT
    space_start = Point(MIN_X, MIN_Y)
    space_end = Point(MAX_X - 1, MAX_Y - 1)

    plaintext_mm = fill_space_plaintext_mm(space_start, space_end)

    # HILBERT INIT
    hc = LinearHilbert(EMMEngine(MAX_X, MAX_Y))
    key = hc.setup(SEC_PARAM)
    hc.build_index(key, plaintext_mm)

    (query_start, query_end) = random_query_2d(space_start, space_end)

    search_tokens = hc.trapdoor(key, query_start, query_end)
    encrypted_results = hc.search(search_tokens)
    resolved_results = hc.resolve(key, encrypted_results)

    num_points = 2 ** (hc.dimension * hc.edge_bits)
    hilbert_points = np.array([hc.hc.point_from_distance(i) for i in range(num_points)])

    plt.figure(figsize=(12, 12))

    plt.plot(hilbert_points[:, 0], hilbert_points[:, 1], color="blue")

    for idx, (x, y) in enumerate(hilbert_points):
        plt.text(x - 0.3, y - 0.2, str(idx), fontsize=6, color="blue")

    for p in plaintext_mm.keys():
        files = plaintext_mm.get(p)

        if resolved_results.isdisjoint(files):
            plt.scatter(p.x, p.y, color="red")
            plt.text(p.x + 0.1, p.y + 0.1, '\n'.join([s.decode('utf-8') for s in files]), fontsize=8)
        else:
            plt.scatter(p.x, p.y, color="green")
            for i, c in enumerate(files):
                if c in resolved_results:
                    label_color = "green"
                else:
                    label_color = "black"
                plt.text(p.x + 0.1, p.y + 0.1 + i * 0.2, c.decode('utf-8'), fontsize=8, color=label_color)


    def plot_rect(p1: Point, p2: Point, color: str, label: str):
        x1 = p1.x - 0.1
        y1 = p1.y - 0.1

        x2 = p2.x + 0.1
        y2 = p2.y + 0.1

        plt.fill([x1, x2, x2, x1], [y1, y1, y2, y2], color=color, alpha=0.1, label=label)


    plot_rect(space_start, space_end, "yellow", "Search Space")
    plot_rect(query_start, query_end, "green", "Query")

    plt.title(f"Hilbert Curve")
    plt.xlabel("X")
    plt.ylabel("Y")
    plt.legend()
    plt.grid(True)
    plt.show()
