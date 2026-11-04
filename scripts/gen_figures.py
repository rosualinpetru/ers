#!/usr/bin/env python3
"""
Generate publication-quality figures for the ERS technical report and blog post.

Runs the real schemes from the `ers-main` package on the dense 2D dataset and
plots trapdoor-generation time, search-token count, index size, the merging
precision/leakage trade-off, and a Hilbert-curve query visualisation.

Usage:  python3 gen_figures.py
Outputs PNG (raster, for the blog) and PDF (vector, for LaTeX) into ./figures/
"""

import os
import random
import statistics as st
import sys
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

# The scripts live in scripts/; the package root is one level up.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from ers.benchmark.util.dataset_generator import generate_dense_database_2d
from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.hilbert.linear_hilbert import LinearHilbert
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.schemes.linear import Linear
from ers.schemes.range_brc import RangeBRC
from ers.structures.hilbert_curve import HilbertCurve
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point

OUT = os.path.join(REPO_ROOT, "figures")
os.makedirs(OUT, exist_ok=True)

# ---- Style -----------------------------------------------------------------
plt.rcParams.update(
    {
        "figure.dpi": 130,
        "savefig.dpi": 150,
        "font.size": 13,
        "axes.titlesize": 14,
        "axes.labelsize": 13,
        "legend.fontsize": 12,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
C_TRAD = "#1b6ca8"  # traditional multi-dimensional schemes (blue)
C_HILB = "#e07b39"  # Hilbert-curve schemes (orange)
SEED = 20260705


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("  wrote", name)


def make_dataset(bits):
    raw = generate_dense_database_2d(bits, 10**9)
    return {Point(list(t)): raw[t] for t in raw}


def random_queries(bits, n, rng):
    """n random axis-aligned rectangles in the [0,2^bits-1]^2 domain."""
    bound = 2**bits
    qs = []
    for _ in range(n):
        x1 = rng.randrange(bound)
        x2 = rng.randrange(bound)
        y1 = rng.randrange(bound)
        y2 = rng.randrange(bound)
        qs.append(HyperRange.from_coords([min(x1, x2), min(y1, y2)], [max(x1, x2), max(y1, y2)]))
    return qs


def index_size_bytes(scheme):
    return sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in scheme.encrypted_db.items())


# ---------------------------------------------------------------------------
# Sweep: trapdoor time, #search tokens, index size vs. domain size
# ---------------------------------------------------------------------------
def sweep(bits_range=range(3, 8), n_queries=40):
    rng = random.Random(SEED)
    rows = {name: {"bits": [], "time": [], "tokens": [], "index": []} for name in ["Linear", "LinearHilbert", "RangeBRC", "RangeBRCHilbert"]}

    pairs = [("Linear", Linear), ("LinearHilbert", LinearHilbert), ("RangeBRC", RangeBRC), ("RangeBRCHilbert", RangeBRCHilbert)]

    for bits in bits_range:
        print(f"[sweep] domain bits = {bits} (domain 2^{2 * bits})")
        data = make_dataset(bits)
        queries = random_queries(bits, n_queries, rng)
        for name, ctor in pairs:
            scheme = ctor(EMMEngine([bits, bits], 2))
            k = scheme.setup(16)
            scheme.build_index(k, data)
            times, tokens = [], []
            for q in queries:
                t0 = time.perf_counter()
                td = scheme.trapdoor(k, q)
                times.append(time.perf_counter() - t0)
                tokens.append(len(td))
            rows[name]["bits"].append(bits)
            rows[name]["time"].append(st.mean(times) * 1e3)  # ms
            rows[name]["tokens"].append(st.mean(tokens))
            rows[name]["index"].append(index_size_bytes(scheme) / 1024)  # KiB
    return rows


def plot_time(rows):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = [2 * b for b in rows["Linear"]["bits"]]
    ax.plot(x, rows["Linear"]["time"], "-o", color=C_TRAD, label="Linear (traditional)")
    ax.plot(x, rows["LinearHilbert"]["time"], "--s", color=C_HILB, label="LinearHilbert")
    ax.plot(x, rows["RangeBRC"]["time"], "-^", color=C_TRAD, label="RangeBRC (traditional)")
    ax.plot(x, rows["RangeBRCHilbert"]["time"], "--D", color=C_HILB, label="RangeBRCHilbert")
    ax.set_yscale("log")
    ax.set_xlabel("Domain size  (log$_2$ |domain|)")
    ax.set_ylabel("Avg. trapdoor time (ms, log scale)")
    ax.set_title("Search-token generation time")
    ax.legend()
    save(fig, "fig_trapdoor_time")


def plot_tokens(rows):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = [2 * b for b in rows["RangeBRC"]["bits"]]
    ax.plot(x, rows["RangeBRC"]["tokens"], "-^", color=C_TRAD, label="RangeBRC (traditional)")
    ax.plot(x, rows["RangeBRCHilbert"]["tokens"], "--D", color=C_HILB, label="RangeBRCHilbert")
    ax.set_xlabel("Domain size  (log$_2$ |domain|)")
    ax.set_ylabel("Avg. # search tokens")
    ax.set_title("Search tokens per query  (query leakage)")
    ax.legend()
    save(fig, "fig_search_tokens")


def plot_index(rows):
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = [2 * b for b in rows["RangeBRC"]["bits"]]
    ax.plot(x, rows["RangeBRC"]["index"], "-^", color=C_TRAD, label="RangeBRC (traditional)")
    ax.plot(x, rows["RangeBRCHilbert"]["index"], "--D", color=C_HILB, label="RangeBRCHilbert")
    ax.set_yscale("log")
    ax.set_xlabel("Domain size  (log$_2$ |domain|)")
    ax.set_ylabel("Encrypted index size (KiB, log scale)")
    ax.set_title("Encrypted index size")
    ax.legend()
    save(fig, "fig_index_size")


# ---------------------------------------------------------------------------
# Merging trade-off: as tolerance grows, tokens drop but false positives rise
# ---------------------------------------------------------------------------
def merge_tradeoff(bits=5, n_queries=60):
    rng = random.Random(SEED + 1)
    data = make_dataset(bits)
    scheme = RangeBRCHilbert(EMMEngine([bits, bits], 2))
    k = scheme.setup(16)
    scheme.build_index(k, data)
    queries = random_queries(bits, n_queries, rng)

    tolerances = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    mean_tokens, mean_prec = [], []
    for tol in tolerances:
        toks, precs = [], []
        for q in queries:
            td = scheme.trapdoor(k, q, tol)
            all_pos = scheme.resolve(k, scheme.search(td))  # decrypted payloads (bytes)
            true_pos = set()
            for p in q.points():
                true_pos |= set(data.get(p, []))
            # correctness sanity: a correct cover never drops a true positive
            assert true_pos.issubset(all_pos), "false negative detected!"
            precs.append(len(true_pos) / len(all_pos) if all_pos else 1.0)
            toks.append(len(td))
        mean_tokens.append(st.mean(toks))
        mean_prec.append(st.mean(precs))
        print(f"[merge] tol={tol:>4}: tokens={st.mean(toks):.2f} precision={st.mean(precs):.3f}")

    fig, ax1 = plt.subplots(figsize=(6.6, 4.2))
    ax2 = ax1.twinx()
    (l1,) = ax1.plot(tolerances, mean_tokens, "-o", color=C_HILB, label="# search tokens")
    (l2,) = ax2.plot(tolerances, mean_prec, "--s", color=C_TRAD, label="precision")
    ax1.set_xlabel("Merging tolerance")
    ax1.set_ylabel("Avg. # search tokens", color=C_HILB)
    ax2.set_ylabel("Avg. precision", color=C_TRAD)
    ax1.tick_params(axis="y", colors=C_HILB)
    ax2.tick_params(axis="y", colors=C_TRAD)
    ax2.set_ylim(0, 1.05)
    ax2.grid(False)
    ax1.set_title(f"Segment merging: leakage vs. precision (domain 2$^{{{2 * bits}}}$)")
    ax1.legend(handles=[l1, l2], loc="center right")
    save(fig, "fig_merge_tradeoff")


# ---------------------------------------------------------------------------
# Hero: Hilbert curve query visualisation (exact vs merged segments)
# ---------------------------------------------------------------------------
def hilbert_query(order=3):
    hc = HilbertCurve(order, 2)
    n = 2 ** (2 * order)
    pts = [hc.point_from_distance(i) for i in range(n)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]

    query = HyperRange.from_coords([1, 1], [4, 2])  # 4x2 rectangle: merges visibly
    q_pts = set((p[0], p[1]) for p in query.points())

    def draw(ax, tolerance, title):
        # full curve (faint)
        ax.plot(xs, ys, color="#cccccc", lw=1.2, zorder=1)
        # query rectangle
        rect = Rectangle(
            (query.start[0] - 0.5, query.start[1] - 0.5),
            query.end[0] - query.start[0] + 1,
            query.end[1] - query.start[1] + 1,
            facecolor="#2e8b57",
            alpha=0.12,
            edgecolor="#2e8b57",
            lw=2,
            zorder=2,
        )
        ax.add_patch(rect)
        # segments returned by the cover
        segments = hc.brc_with_merging(query, tolerance)
        for s, e in segments:
            seg_pts = [hc.point_from_distance(d) for d in range(s, e + 1)]
            sx = [p[0] for p in seg_pts]
            sy = [p[1] for p in seg_pts]
            ax.plot(sx, sy, color=C_HILB, lw=3.4, zorder=4, solid_capstyle="round")
        # points: green = true positive (in query), red = false positive (covered but outside)
        covered = set()
        for s, e in segments:
            for d in range(s, e + 1):
                p = hc.point_from_distance(d)
                covered.add((p[0], p[1]))
        for x, y in [(p[0], p[1]) for p in pts]:
            if (x, y) in q_pts:
                col, z = "#2e8b57", 6
            elif (x, y) in covered:
                col, z = "#d1495b", 6  # false positive
            else:
                col, z = "#9aa0a6", 3
            ax.scatter([x], [y], s=70, color=col, zorder=z, edgecolors="white", linewidths=0.6)
        for i, p in enumerate(pts):
            ax.text(p[0] + 0.12, p[1] + 0.12, str(i), fontsize=7.5, color="#555", zorder=7)
        ax.set_title(title)
        ax.set_xlim(-0.7, 2**order - 0.3)
        ax.set_ylim(-0.7, 2**order - 0.3)
        ax.set_aspect("equal")
        ax.set_xticks(range(2**order))
        ax.set_yticks(range(2**order))
        ax.grid(True, alpha=0.25)

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 6.2))
    n_exact = len(hc.brc_with_merging(query, 0))
    n_merged = len(hc.brc_with_merging(query, 1))
    draw(a, 0, f"Exact cover ($\\tau=0$)\n{n_exact} segments  $\\cdot$  precision 1.0")
    draw(b, 1, f"Merged cover ($\\tau=1$)\n{n_merged} segments  $\\cdot$  false positives in red")
    legend = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2e8b57", markersize=11, label="true positive (in query)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d1495b", markersize=11, label="false positive (merged in)"),
        Line2D([0], [0], color=C_HILB, lw=3.4, label="queried Hilbert segment(s)"),
    ]
    fig.legend(handles=legend, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle("Mapping a 2D range query onto Hilbert-curve segments (order 3, 8$\\times$8)", y=0.99, fontsize=15)
    fig.subplots_adjust(bottom=0.12, top=0.86, wspace=0.15)
    save(fig, "fig_hilbert_query")


# ---------------------------------------------------------------------------
# Plain Hilbert curve of a few orders (illustrative, for background section)
# ---------------------------------------------------------------------------
def hilbert_orders():
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    for ax, order in zip(axes, (1, 2, 3)):
        hc = HilbertCurve(order, 2)
        n = 2 ** (2 * order)
        pts = [hc.point_from_distance(i) for i in range(n)]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        ax.plot(xs, ys, "-", color=C_HILB, lw=2.2)
        ax.scatter(xs, ys, s=18, color=C_TRAD, zorder=3)
        ax.set_title(f"Order {order}  ({2**order}$\\times${2**order})")
        ax.set_aspect("equal")
        ax.axis("off")
    fig.suptitle("Hilbert space-filling curve at increasing order", y=1.02)
    fig.tight_layout()
    save(fig, "fig_hilbert_orders")


if __name__ == "__main__":
    print("== Hilbert illustrations ==")
    hilbert_orders()
    hilbert_query()
    print("== Merging trade-off ==")
    merge_tradeoff()
    print("== Performance sweep ==")
    rows = sweep()
    plot_time(rows)
    plot_tokens(rows)
    plot_index(rows)
    # dump raw numbers for the report
    import json

    with open(os.path.join(OUT, "sweep_data.json"), "w") as f:
        json.dump(rows, f, indent=2)
    print("Done. Figures in", OUT)
