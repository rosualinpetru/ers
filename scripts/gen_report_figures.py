#!/usr/bin/env python3
"""
Figures and tables for the paper, generated from the benchmark reports.

Reads every ``.xlsx`` report under a benchmarks folder (default ``benchmarks/``),
keeps the latest report per (scheme, dataset, dimensions, bits), and writes
publication figures (PDF + PNG) and LaTeX tables into an output folder. Nothing
is hand-entered: every number in the paper's evaluation comes from here.

Usage::

    python3 scripts/gen_report_figures.py [--benchmarks benchmarks] [--out figures/report]

Visual encoding (shared with the Dash report site): hue = scheme family;
marker shape = domain and divider (native: circle / diamond / square for
uniform / cell-balanced / record-balanced; Hilbert: triangle-up / triangle-down
/ X); Hilbert series are additionally dashed.
"""

import argparse
import glob
import os
import re
import statistics as st
import sys
from typing import Any, Dict, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import openpyxl
from matplotlib.ticker import LogLocator, NullFormatter, ScalarFormatter

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from ers.benchmark.plot.plot_benchmarks import FAMILY_COLORS, parse_scheme  # noqa: E402

# --------------------------------------------------------------------------- #
# Style.
# --------------------------------------------------------------------------- #
INK, INK_2, INK_MUTED, GRID = "#0b0b0b", "#52514e", "#898781", "#e1e0d9"
plt.rcParams.update(
    {
        "figure.dpi": 130,
        "savefig.dpi": 200,
        "font.size": 10,
        "axes.titlesize": 10.5,
        "axes.labelsize": 10,
        "legend.fontsize": 8.5,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "axes.edgecolor": "#c3c2b7",
        "axes.labelcolor": INK_2,
        "xtick.color": INK_2,
        "ytick.color": INK_2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.frameon": False,
        "lines.linewidth": 2.1,
        "lines.markersize": 7,
        "lines.markeredgewidth": 0.9,
        "lines.markeredgecolor": "white",
        "pdf.fonttype": 42,
    }
)
COL_W, DBL_W = 3.45, 7.1  # IEEE column / page widths in inches

PRETTY = {
    "linear": "Linear",
    "linear_hilbert": "LinearHilbert",
    "range_brc": "RangeBRC",
    "range_brc_hilbert": "RangeBRC-H",
    "range_brc_data_dependent": "RangeBRC-DD",
    "range_brc_hilbert_data_dependent": "RangeBRC-H-DD",
    "tdag_src": "TdagSRC",
    "tdag_src_hilbert": "TdagSRC-H",
    "tdag_src_data_dependent": "TdagSRC-DD",
    "tdag_src_hilbert_data_dependent": "TdagSRC-H-DD",
    "quad_brc": "QuadBRC",
    "quad_brc_hilbert": "QuadBRC-H",
    "quad_brc_data_dependent": "QuadBRC-DD",
    "quad_brc_hilbert_data_dependent": "QuadBRC-H-DD",
    "quad_src": "QuadSRC",
    "quad_src_hilbert": "QuadSRC-H",
    "quad_src_data_dependent": "QuadSRC-DD",
    "quad_src_hilbert_data_dependent": "QuadSRC-H-DD",
    "rtree": "RTree (STR)",
    "hilbert_rtree": "HilbertRTree",
    "interactive_src": "Interactive",
    "interactive_src_hilbert": "Interactive-H",
    "range_brc_data_dependent_records": "RangeBRC-DDr",
    "quad_brc_data_dependent_records": "QuadBRC-DDr",
    "quad_src_data_dependent_records": "QuadSRC-DDr",
    "tdag_src_data_dependent_records": "TdagSRC-DDr",
    "range_brc_hilbert_data_dependent_records": "RangeBRC-H-DDr",
    "quad_brc_hilbert_data_dependent_records": "QuadBRC-H-DDr",
    "quad_src_hilbert_data_dependent_records": "QuadSRC-H-DDr",
    "tdag_src_hilbert_data_dependent_records": "TdagSRC-H-DDr",
}


#: Marker by (domain, divider). Shape alone must separate native from Hilbert
#: in a legend; the dashed line is a second cue, not the only one.
MARKERS = {
    (False, "uniform"): "o",  # native, uniform
    (False, "cells"): "D",  # native, cell-balanced
    (False, "records"): "s",  # native, record-balanced
    (True, "uniform"): "^",  # Hilbert, uniform
    (True, "cells"): "v",  # Hilbert, cell-balanced
    (True, "records"): "X",  # Hilbert, record-balanced
}


def style(scheme: str) -> dict:
    t = parse_scheme(scheme)
    divider = ("records" if t["records"] else "cells") if t["data_dependent"] else "uniform"
    return {
        "color": FAMILY_COLORS[t["family"]],
        "linestyle": "--" if t["hilbert"] else "-",
        "marker": MARKERS[(t["hilbert"], divider)],
        "markersize": 8 if t["hilbert"] else 7,
    }


# --------------------------------------------------------------------------- #
# Loading.
# --------------------------------------------------------------------------- #
NAME_RE = re.compile(
    r"^(?P<scheme>.+?)_(?P<dataset>cali|spitz|gowalla|nh_64|dense_2d|dense_3d|random_2d)_(?P<dims>\d+)_(?P<bits>\d+)_(?P<records>\d+)_(?P<queries>\d+)_(?P<ts>\d{8}_\d{6})\.xlsx$"
)

Key = Tuple[str, str, int, int]  # scheme, dataset, dims, bits


class Reports:
    """The latest report per key, as ``metric -> {bucket: value}`` plus scalar sheets."""

    def __init__(self, folder: str):
        latest: Dict[Key, Tuple[str, str]] = {}
        for path in glob.glob(os.path.join(folder, "*.xlsx")):
            m = NAME_RE.match(os.path.basename(path))
            if not m:
                continue
            key = (m["scheme"], m["dataset"], int(m["dims"]), int(m["bits"]))
            if key not in latest or latest[key][0] < m["ts"]:
                latest[key] = (m["ts"], path)
        self.data: Dict[Key, Dict[str, Dict[Optional[int], float]]] = {}
        for key, (_, path) in latest.items():
            wb = openpyxl.load_workbook(path, read_only=True)
            sheets: Dict[str, Dict[Optional[int], float]] = {}
            for name in wb.sheetnames:
                rows = [r for r in wb[name].iter_rows(values_only=True) if r and r[0] is not None]
                cells: List[Any] = [list(r) for r in rows]
                if name in ("index_time", "index_size"):
                    sheets[name] = {None: float(cells[0][0])}
                else:
                    sheets[name] = {int(r[0]): float(r[1]) for r in cells if r[1] is not None}
            self.data[key] = sheets

    def scalar(self, scheme: str, dataset: str, dims: int, bits: int, metric: str) -> Optional[float]:
        sheets = self.data.get((scheme, dataset, dims, bits))
        if not sheets or metric not in sheets:
            return None
        return sheets[metric].get(None)

    def buckets(self, scheme: str, dataset: str, dims: int, bits: int, metric: str) -> Dict[int, float]:
        sheets = self.data.get((scheme, dataset, dims, bits))
        if not sheets or metric not in sheets:
            return {}
        vals = {b: v for b, v in sheets[metric].items() if b is not None}
        if metric == "precision":
            # -1 = exact by construction; -inf = false negative (never plot).
            vals = {b: (1.0 if v == -1 else v) for b, v in vals.items() if v != float("-inf")}
        return vals

    def mean(self, scheme: str, dataset: str, dims: int, bits: int, metric: str) -> Optional[float]:
        vals = self.buckets(scheme, dataset, dims, bits, metric)
        return st.mean(vals.values()) if vals else None

    def bits_for(self, scheme: str, dataset: str, dims: int) -> List[int]:
        return sorted(b for (s, d, dd, b) in self.data if s == scheme and d == dataset and dd == dims)


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #
def save(fig, out: str, name: str):
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(out, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("  wrote", name)


def log_y(ax, dense: bool = False):
    """Log y-axis with plain-number labels: decades only, or 1-2-5 steps for narrow ranges."""
    ax.set_yscale("log")
    ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0) if dense else (1.0,)))
    fmt = ScalarFormatter()
    fmt.set_scientific(False)
    ax.yaxis.set_major_formatter(fmt)
    ax.yaxis.set_minor_formatter(NullFormatter())


def domain_ticks(ax, bits_list: List[int], dims: int):
    ax.set_xticks(bits_list)
    ax.set_xticklabels([f"$2^{{{dims * b}}}$" for b in bits_list])
    ax.set_xlabel("domain size (cells)")


def series_vs_domain(
    ax, R: Reports, schemes: List[str], dataset: str, dims: int, metric: str, scalar: bool = False, label_right: bool = True, scale: float = 1.0
):
    """One line per scheme over domain size; direct label at the right end."""
    handles = []
    ends = []
    for s in schemes:
        xs = R.bits_for(s, dataset, dims)
        pts = []
        for b in xs:
            v = R.scalar(s, dataset, dims, b, metric) if scalar else R.mean(s, dataset, dims, b, metric)
            if v is not None:
                pts.append((b, v * scale))
        if not pts:
            continue
        (h,) = ax.plot([p[0] for p in pts], [p[1] for p in pts], label=PRETTY[s], **style(s))
        handles.append(h)
        ends.append((pts[-1][0], pts[-1][1], PRETTY[s], style(s)["color"]))
    if label_right and len(ends) <= 4:
        for x, y, name, c in ends:
            ax.annotate(name, (x, y), xytext=(5, 0), textcoords="offset points", fontsize=8.5, color=INK_2, va="center")
    return handles


def fmt_bytes(v: Optional[float]) -> str:
    if v is None:
        return "--"
    for unit, div in (("GB", 1e9), ("MB", 1e6), ("kB", 1e3)):
        if v >= div:
            return f"{v / div:.1f}\\,{unit}"
    return f"{v:.0f}\\,B"


def fmt_num(v: Optional[float], digits: int = 0) -> str:
    if v is None:
        return "--"
    if digits == 0:
        return f"{v:,.0f}"
    return f"{v:.{digits}f}"


# --------------------------------------------------------------------------- #
# Figures.
# --------------------------------------------------------------------------- #
def fig_exact_tokens_index(R: Reports, out: str):
    """Exact schemes on cali: tokens and index size vs domain (two panels, two charts, one axis each)."""
    schemes = ["linear", "range_brc", "quad_brc", "range_brc_hilbert"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(DBL_W, 3.0))
    series_vs_domain(a1, R, schemes, "cali", 2, "trapdoor_count")
    log_y(a1)
    a1.set_ylabel("tokens per query (mean)")
    a1.set_title("Tokens (query leakage)")
    domain_ticks(a1, [5, 6, 7], 2)
    series_vs_domain(a2, R, schemes, "cali", 2, "index_size", scalar=True, scale=1e-6)
    log_y(a2, dense=True)
    a2.set_ylabel("index size (MB)")
    a2.set_title("Server storage")
    domain_ticks(a2, [5, 6, 7], 2)
    fig.legend(*a1.get_legend_handles_labels(), loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, out, "fig_exact_cali")


def fig_lossy_precision_vs_size(R: Reports, out: str):
    """Precision by query-size bucket at cali 2^12: the lossy schemes."""
    schemes = ["quad_src", "tdag_src", "hilbert_rtree", "rtree", "interactive_src_hilbert", "interactive_src"]
    fig, ax = plt.subplots(figsize=(COL_W, 3.0))
    for s in schemes:
        vals = R.buckets(s, "cali", 2, 6, "precision")
        if not vals:
            continue
        xs = sorted(vals)
        ax.plot([x + 5 for x in xs], [vals[x] for x in xs], label=PRETTY[s], **style(s))
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("query size (% of domain area)")
    ax.set_ylabel("precision")
    ax.set_title("Precision vs query size, cali, domain $2^{12}$")
    fig.legend(*ax.get_legend_handles_labels(), loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, out, "fig_precision_vs_query_size")


def fig_lossy_vs_domain(R: Reports, out: str):
    """Lossy schemes: precision and tokens vs domain on cali."""
    schemes = ["quad_src", "tdag_src", "hilbert_rtree", "rtree", "interactive_src_hilbert", "interactive_src"]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(DBL_W, 3.0))
    series_vs_domain(a1, R, schemes, "cali", 2, "precision", label_right=False)
    a1.set_ylim(0, 1.02)
    a1.set_ylabel("precision (mean)")
    a1.set_title("Precision")
    domain_ticks(a1, [5, 6, 7], 2)
    # Single-cover schemes issue exactly one token by construction: not plotted.
    series_vs_domain(a2, R, [s for s in schemes if "src" not in s or "interactive" in s], "cali", 2, "trapdoor_count", label_right=False)
    log_y(a2)
    a2.set_ylabel("tokens per query (mean)")
    a2.set_title("Tokens, multi-token schemes")
    domain_ticks(a2, [5, 6, 7], 2)
    fig.legend(*a1.get_legend_handles_labels(), loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, out, "fig_lossy_cali")


def fig_data_dependent(R: Reports, out: str):
    """Uniform vs mass-balanced dividers: tokens of the BRC schemes on cali and spitz."""
    pairs = [
        ("range_brc", "range_brc_data_dependent"),
        ("range_brc_hilbert", "range_brc_hilbert_data_dependent"),
        ("quad_brc_hilbert", "quad_brc_hilbert_data_dependent"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(DBL_W, 3.0), sharey=True)
    for ax, ds in zip(axes, ["cali", "spitz"]):
        for u, d in pairs:
            series_vs_domain(ax, R, [u, d], ds, 2, "trapdoor_count", label_right=False)
        log_y(ax)
        ax.set_title(ds)
        domain_ticks(ax, [5, 6, 7], 2)
    axes[0].set_ylabel("tokens per query (mean)")
    fig.legend(*axes[0].get_legend_handles_labels(), loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, out, "fig_data_dependent")


#: One representative scheme per distinct encrypted index. BRC and SRC share
#: the structure (hence the index), the quadtree is the same on the grid and on
#: the curve, and so is the linear index.
STRUCTURES = [
    ("linear", "Linear (= Linear-H)"),
    ("range_brc", "Range product"),
    ("range_brc_data_dependent", "Range product-DD"),
    ("range_brc_data_dependent_records", "Range product-DDr"),
    ("range_brc_hilbert", "Range tree-H"),
    ("range_brc_hilbert_data_dependent", "Range tree-H-DD"),
    ("range_brc_hilbert_data_dependent_records", "Range tree-H-DDr"),
    ("tdag_src", "TDAG product"),
    ("tdag_src_data_dependent", "TDAG product-DD"),
    ("tdag_src_data_dependent_records", "TDAG product-DDr"),
    ("tdag_src_hilbert", "TDAG-H"),
    ("tdag_src_hilbert_data_dependent", "TDAG-H-DD"),
    ("tdag_src_hilbert_data_dependent_records", "TDAG-H-DDr"),
    ("quad_brc", "Quadtree (= -H)"),
    ("quad_brc_data_dependent", "Quadtree-DD"),
    ("quad_brc_data_dependent_records", "Quadtree-DDr"),
    ("quad_brc_hilbert_data_dependent", "Quadtree-H-DD"),
    ("quad_brc_hilbert_data_dependent_records", "Quadtree-H-DDr"),
    ("rtree", "R-tree (STR)"),
    ("hilbert_rtree", "Hilbert R-tree"),
    ("interactive_src", "Interactive (2 indices)"),
    ("interactive_src_hilbert", "Interactive-H (2 indices)"),
]


def fig_index_size_bars(R: Reports, out: str):
    """Ranked horizontal bars: index size of every distinct structure at cali 2^12."""
    rows = []
    for s, label in STRUCTURES:
        v = R.scalar(s, "cali", 2, 6, "index_size")
        if v is not None:
            rows.append((label, v, style(s)["color"]))
    rows.sort(key=lambda r: r[1])
    fig, ax = plt.subplots(figsize=(COL_W, 5.0))
    ys = range(len(rows))
    ax.barh(list(ys), [r[1] / 1e6 for r in rows], color=[r[2] for r in rows], height=0.72)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([r[0] for r in rows], fontsize=8.5)
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(LogLocator(base=10, subs=(1.0,)))
    fmt = ScalarFormatter()
    fmt.set_scientific(False)
    ax.xaxis.set_major_formatter(fmt)
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.set_xlabel("index size (MB, log)")
    ax.set_title("Index size per structure, cali, domain $2^{12}$")
    for y, r in zip(ys, rows):
        ax.annotate(fmt_bytes(r[1]).replace("\\,", " "), (r[1] / 1e6, y), xytext=(3, 0), textcoords="offset points", fontsize=8, va="center", color=INK_2)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    save(fig, out, "fig_index_size_cali")


#: On nh_64 every occupied cell holds one record, so record weighting is the
#: cell weighting; the curve quadtree and the curve linear scheme are the native
#: ones by construction. None of these adds a row.
NH_DUPLICATES = {"linear_hilbert", "quad_brc_hilbert", "quad_src_hilbert"} | {s for s in PRETTY if s.endswith("_records")}


def fig_nh3d(R: Reports, out: str):
    """3D (nh_64): tokens and precision per scheme, ranked bars."""
    rows = []
    for s in PRETTY:
        if s in NH_DUPLICATES:
            continue
        tok = R.mean(s, "nh_64", 3, 6, "trapdoor_count")
        if tok is None:
            continue
        rows.append((PRETTY[s], tok, R.mean(s, "nh_64", 3, 6, "precision"), R.scalar(s, "nh_64", 3, 6, "index_size"), style(s)["color"]))
    # Not plotted: single-cover schemes' token count (always 1) and exact schemes' precision (always 1).
    tok_rows = sorted([r for r in rows if r[1] > 1], key=lambda r: r[1])
    prec_rows = sorted([r for r in rows if r[2] is not None and r[2] < 1], key=lambda r: r[2])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(DBL_W, 3.4), gridspec_kw={"width_ratios": [1.3, 1]})
    ys = list(range(len(tok_rows)))
    a1.barh(ys, [r[1] for r in tok_rows], color=[r[4] for r in tok_rows], height=0.72)
    a1.set_yticks(ys)
    a1.set_yticklabels([r[0] for r in tok_rows], fontsize=8.5)
    a1.set_xscale("log")
    a1.set_xlabel("tokens per query (mean, log)")
    a1.set_title("Tokens, multi-token schemes")
    for y, r in zip(ys, tok_rows):
        a1.annotate(fmt_num(r[1]), (r[1], y), xytext=(3, 0), textcoords="offset points", fontsize=8, va="center", color=INK_2)
    a1.grid(axis="y", visible=False)
    ys2 = list(range(len(prec_rows)))
    a2.barh(ys2, [r[2] for r in prec_rows], color=[r[4] for r in prec_rows], height=0.72)
    a2.set_yticks(ys2)
    a2.set_yticklabels([r[0] for r in prec_rows], fontsize=8.5)
    a2.set_xlim(0, 1.05)
    a2.set_xlabel("precision (mean)")
    a2.set_title("Precision, lossy schemes")
    for y, r in zip(ys2, prec_rows):
        a2.annotate(f"{r[2]:.2f}", (r[2], y), xytext=(3, 0), textcoords="offset points", fontsize=8, va="center", color=INK_2)
    a2.grid(axis="y", visible=False)
    fig.tight_layout()
    save(fig, out, "fig_nh64")


def fig_interactive_rounds(R: Reports, out: str):
    """Round-two tokens of the two interactive variants, cali and spitz (round one is always one token)."""
    fig, axes = plt.subplots(1, 2, figsize=(DBL_W, 2.9), sharey=True)
    for ax, ds in zip(axes, ["cali", "spitz"]):
        labels, r2, cols = [], [], []
        for s in ["interactive_src", "interactive_src_hilbert"]:
            for b in R.bits_for(s, ds, 2):
                labels.append(f"{'native' if s == 'interactive_src' else 'Hilbert'}\n$2^{{{2 * b}}}$")
                r2.append(R.mean(s, ds, 2, b, "trapdoor_count_round2") or 0)
                cols.append(style(s)["color"])
        xs = range(len(labels))
        ax.bar(xs, r2, color=cols, width=0.7, edgecolor="white", linewidth=1)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(labels, fontsize=8.5)
        ax.set_title(ds)
        for x, v in zip(xs, r2):
            ax.annotate(f"{v:.0f}", (x, v), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8.5, color=INK_2)
        ax.grid(axis="x", visible=False)
    axes[0].set_ylabel("round-two tokens per query (mean)")
    fig.tight_layout()
    save(fig, out, "fig_interactive_rounds")


def fig_precision_datasets(R: Reports, out: str):
    """Small multiples: precision vs domain for the lossy schemes on three datasets."""
    schemes = ["quad_src", "tdag_src", "tdag_src_hilbert", "hilbert_rtree", "rtree", "interactive_src_hilbert"]
    fig, axes = plt.subplots(1, 3, figsize=(DBL_W, 2.9), sharey=True)
    for ax, (ds, bl) in zip(axes, [("dense_2d", [3, 4, 5]), ("cali", [5, 6, 7]), ("spitz", [5, 6, 7])]):
        series_vs_domain(ax, R, schemes, ds, 2, "precision", label_right=False)
        ax.set_ylim(0, 1.02)
        ax.set_title(ds)
        domain_ticks(ax, bl, 2)
    axes[0].set_ylabel("precision (mean)")
    fig.legend(*axes[1].get_legend_handles_labels(), loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    save(fig, out, "fig_precision_datasets")


def fig_mass_weighting(R: Reports, out: str):
    """Cell- vs record-balanced dividers: tokens of the BRC schemes and precision of the SRC schemes."""
    brc = [
        ("range_brc", "range_brc_data_dependent", "range_brc_data_dependent_records"),
        ("quad_brc", "quad_brc_data_dependent", "quad_brc_data_dependent_records"),
    ]
    src = [
        ("quad_src", "quad_src_data_dependent", "quad_src_data_dependent_records"),
        ("tdag_src", "tdag_src_data_dependent", "tdag_src_data_dependent_records"),
    ]
    fig, axes = plt.subplots(1, 2, figsize=(DBL_W, 3.0))
    for triple in brc:
        series_vs_domain(axes[0], R, list(triple), "spitz", 2, "trapdoor_count", label_right=False)
    log_y(axes[0], dense=True)
    axes[0].set_ylabel("tokens per query (mean)")
    axes[0].set_title("BRC schemes, spitz: tokens")
    domain_ticks(axes[0], [5, 6, 7], 2)
    for triple in src:
        series_vs_domain(axes[1], R, list(triple), "spitz", 2, "precision", label_right=False)
    axes[1].set_ylim(0, 1.02)
    axes[1].set_ylabel("precision (mean)")
    axes[1].set_title("SRC schemes, spitz: precision")
    domain_ticks(axes[1], [5, 6, 7], 2)
    h0, l0 = axes[0].get_legend_handles_labels()
    h1, l1 = axes[1].get_legend_handles_labels()
    fig.legend(h0 + h1, l0 + l1, loc="lower center", ncol=6, bbox_to_anchor=(0.5, -0.08), fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 1, 1))
    save(fig, out, "fig_mass_weighting")


def table_weighting(R: Reports, out: str):
    """Uniform vs cell-weighted vs record-weighted dividers, every dataset at its largest 2D domain and 3D."""
    bases = ["range_brc", "quad_brc", "range_brc_hilbert", "quad_brc_hilbert", "quad_src", "tdag_src", "quad_src_hilbert", "tdag_src_hilbert"]
    configs = [("cali", 2, 7), ("spitz", 2, 7)]
    lines = ["\\begin{tabular}{l " + " ".join("rrr" for _ in configs) + "}", "\\toprule"]
    lines.append(" & " + " & ".join(f"\\multicolumn{{3}}{{c}}{{{d.replace('_', chr(92) + '_')} $2^{{{dims * b}}}$}}" for d, dims, b in configs) + " \\\\")
    lines.append("".join(f"\\cmidrule(lr){{{2 + 3 * i}-{4 + 3 * i}}}" for i in range(len(configs))))
    lines.append("scheme & " + " & ".join("unif. & cells & rec." for _ in configs) + " \\\\")
    lines.append("\\midrule")
    for base in bases:
        metric = "precision" if "src" in base else "trapdoor_count"
        cells = []
        for d, dims, b in configs:
            for variant in (base, base + "_data_dependent", base + "_data_dependent_records"):
                v = R.mean(variant, d, dims, b, metric)
                cells.append("--" if v is None else (fmt_num(v, 2) if metric == "precision" else fmt_num(v)))
        lines.append(f"{PRETTY[base]} ({'prec.' if metric == 'precision' else 'tokens'}) & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(out, "tab_weighting.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("  wrote tab_weighting.tex")


# --------------------------------------------------------------------------- #
# Tables.
# --------------------------------------------------------------------------- #
def table_main(R: Reports, out: str):
    """The headline table: tokens / precision / index size on cali at 2^10, 2^12, 2^14."""
    order = [
        "linear",
        "range_brc",
        "quad_brc",
        "range_brc_hilbert",
        "quad_src",
        "tdag_src",
        "tdag_src_hilbert",
        "range_brc_data_dependent",
        "range_brc_hilbert_data_dependent",
        "quad_brc_hilbert_data_dependent",
        "tdag_src_data_dependent",
        "tdag_src_hilbert_data_dependent",
        "range_brc_data_dependent_records",
        "quad_brc_data_dependent_records",
        "range_brc_hilbert_data_dependent_records",
        "quad_brc_hilbert_data_dependent_records",
        "quad_src_data_dependent_records",
        "tdag_src_data_dependent_records",
        "quad_src_hilbert_data_dependent_records",
        "tdag_src_hilbert_data_dependent_records",
        "rtree",
        "hilbert_rtree",
        "interactive_src",
        "interactive_src_hilbert",
    ]
    lines = [
        "\\begin{tabular}{l rrr rrr r}",
        "\\toprule",
        " & \\multicolumn{3}{c}{tokens / query} & \\multicolumn{3}{c}{precision} & index \\\\",
        "\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}",
        "scheme & $2^{10}$ & $2^{12}$ & $2^{14}$ & $2^{10}$ & $2^{12}$ & $2^{14}$ & $2^{14}$ \\\\",
        "\\midrule",
    ]
    for s in order:
        toks = [R.mean(s, "cali", 2, b, "trapdoor_count") for b in (5, 6, 7)]
        precs = [R.mean(s, "cali", 2, b, "precision") for b in (5, 6, 7)]
        if all(t is None for t in toks):
            continue
        idx = R.scalar(s, "cali", 2, 7, "index_size")
        if idx is None:
            idx = R.scalar(s, "cali", 2, 6, "index_size")
            idx_s = fmt_bytes(idx) + "$^{\\dagger}$" if idx else "--"
        else:
            idx_s = fmt_bytes(idx)
        name = PRETTY[s].replace("_", "\\_")
        cells = [fmt_num(t) for t in toks] + [("1" if p == 1.0 else fmt_num(p, 2)) for p in precs]
        lines.append(f"{name} & " + " & ".join(cells) + f" & {idx_s} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(out, "tab_cali.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("  wrote tab_cali.tex")


def table_nh(R: Reports, out: str):
    lines = ["\\begin{tabular}{l r r r}", "\\toprule", "scheme & tokens / query & precision & index \\\\", "\\midrule"]
    rows = []
    for s in PRETTY:
        if s in NH_DUPLICATES:
            continue
        tok = R.mean(s, "nh_64", 3, 6, "trapdoor_count")
        idx = R.scalar(s, "nh_64", 3, 6, "index_size")
        if tok is None and idx is None:
            continue
        rows.append((PRETTY[s], tok, R.mean(s, "nh_64", 3, 6, "precision"), idx))
    rows.sort(key=lambda r: (r[1] is None, r[1] or 0))
    for name, tok, prec, idx in rows:
        p = "--" if prec is None else ("1" if prec == 1.0 else fmt_num(prec, 2))
        lines.append(f"{name} & {fmt_num(tok) if tok is not None else '--$^{\\ddagger}$'} & {p} & {fmt_bytes(idx)} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(out, "tab_nh64.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("  wrote tab_nh64.tex")


def table_coverage(R: Reports, out: str):
    """Which (scheme, dataset) pairs have query results at which domain sizes."""
    datasets = [("dense_2d", 2), ("cali", 2), ("spitz", 2), ("nh_64", 3)]
    header = "scheme & " + " & ".join(d.replace("_", "\\_") for d, _ in datasets) + " \\\\"
    lines = ["\\begin{tabular}{l " + "c" * len(datasets) + "}", "\\toprule", header, "\\midrule"]
    for s in PRETTY:
        cells = []
        for d, dims in datasets:
            bs = [b for b in R.bits_for(s, d, dims) if R.mean(s, d, dims, b, "trapdoor_count") is not None]
            cells.append(", ".join(f"$2^{{{dims * b}}}$" for b in bs) if bs else "--")
        lines.append(PRETTY[s] + " & " + " & ".join(cells) + " \\\\")
    lines += ["\\bottomrule", "\\end{tabular}"]
    with open(os.path.join(out, "tab_coverage.tex"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("  wrote tab_coverage.tex")


def dump_numbers(R: Reports, out: str):
    """A flat CSV of every mean metric, for the prose and for checking the tables."""
    import csv

    with open(os.path.join(out, "summary.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["scheme", "dataset", "dims", "bits", "tokens", "precision", "index_size", "search_count", "index_time", "tokens_round1", "tokens_round2"])
        for s, d, dims, b in sorted(R.data):
            w.writerow(
                [
                    s,
                    d,
                    dims,
                    b,
                    R.mean(s, d, dims, b, "trapdoor_count"),
                    R.mean(s, d, dims, b, "precision"),
                    R.scalar(s, d, dims, b, "index_size"),
                    R.mean(s, d, dims, b, "search_count"),
                    R.scalar(s, d, dims, b, "index_time"),
                    R.mean(s, d, dims, b, "trapdoor_count_round1"),
                    R.mean(s, d, dims, b, "trapdoor_count_round2"),
                ]
            )
    print("  wrote summary.csv")


def main():
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--benchmarks", default=os.path.join(REPO_ROOT, "benchmarks"))
    ap.add_argument("--out", default=os.path.join(REPO_ROOT, "figures", "report"))
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    R = Reports(args.benchmarks)
    print(f"loaded {len(R.data)} reports from {args.benchmarks}")
    fig_exact_tokens_index(R, args.out)
    fig_lossy_precision_vs_size(R, args.out)
    fig_lossy_vs_domain(R, args.out)
    fig_data_dependent(R, args.out)
    fig_index_size_bars(R, args.out)
    fig_nh3d(R, args.out)
    fig_interactive_rounds(R, args.out)
    fig_precision_datasets(R, args.out)
    fig_mass_weighting(R, args.out)
    table_main(R, args.out)
    table_weighting(R, args.out)
    table_nh(R, args.out)
    table_coverage(R, args.out)
    dump_numbers(R, args.out)
    print("Done. Output in", args.out)


if __name__ == "__main__":
    main()
