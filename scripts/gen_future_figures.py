#!/usr/bin/env python3
"""
Benchmarks and figures for the *future-work* schemes added on top of the base
ERS framework:

  1. the interactive double-index scheme (Demertzis Logarithmic-SRC-i), 1-D and
     Hilbert-linearised, vs. the non-interactive Hilbert SRC baseline;
  2. the packed Hilbert R-tree vs. the binary-tree RangeBRCHilbert;
  3. data-dependent (density / "probability"-based) indexing vs. uniform, on
     skewed data.

Outputs PNG (for the blog) and PDF (for the report) into ./figures/.
Run:  python3 gen_future_figures.py
"""

import json
import os
import random
import statistics as st
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

# The scripts live in scripts/; the package root is one level up.
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from ers.benchmark.util.dataset_generator import generate_spitz
from ers.schemes.common.emm_engine import EMMEngine
from ers.schemes.dependent.range_brc_data_dependent import RangeBRCDataDependent
from ers.schemes.hilbert.hilbert_rtree_scheme import HilbertRTreeScheme
from ers.schemes.hilbert.interactive_src_hilbert import InteractiveSRCHilbert
from ers.schemes.hilbert.range_brc_hilbert import RangeBRCHilbert
from ers.schemes.hilbert.tdag_src_hilbert import TdagSRCHilbert
from ers.schemes.range_brc import RangeBRC
from ers.structures.hyperrange import HyperRange
from ers.structures.point import Point

OUT = os.path.join(REPO_ROOT, "figures")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 130,
        "savefig.dpi": 150,
        "font.size": 13,
        "axes.titlesize": 14,
        "axes.labelsize": 13,
        "legend.fontsize": 11,
        "axes.grid": True,
        "grid.alpha": 0.3,
        "axes.spines.top": False,
        "axes.spines.right": False,
    }
)
C_BASE = "#1b6ca8"  # baseline / non-interactive
C_NEW = "#e07b39"  # new scheme
C_THIRD = "#2e8b57"  # third series
SEED = 20260705


def save(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)
    print("  wrote", name)


def rects(bits, n, rng):
    b = 2**bits
    out = []
    for _ in range(n):
        x1, x2 = sorted((rng.randrange(b), rng.randrange(b)))
        y1, y2 = sorted((rng.randrange(b), rng.randrange(b)))
        out.append(HyperRange.from_coords([x1, y1], [x2, y2]))
    return out


def true_positives(query, mm):
    tp = set()
    for x in range(query.start[0], query.end[0] + 1):
        for y in range(query.start[1], query.end[1] + 1):
            p = Point([x, y])
            if p in mm:
                tp |= set(mm[p])
    return tp


def sparse_2d(bits, n_points, rng):
    b = 2**bits
    mm = {}
    for _ in range(n_points):
        p = Point([rng.randrange(b), rng.randrange(b)])
        mm.setdefault(p, []).append((f"d_{p[0]}_{p[1]}").encode())
    return mm


def clustered_2d(bits, n_points, rng, n_clusters=4):
    """Skewed data: points drawn from a few Gaussian blobs (favours density indexing)."""
    b = 2**bits
    centers = [(rng.randrange(b), rng.randrange(b)) for _ in range(n_clusters)]
    mm = {}
    sigma = max(1, b // 12)
    for _ in range(n_points):
        cx, cy = rng.choice(centers)
        x = min(b - 1, max(0, int(rng.gauss(cx, sigma))))
        y = min(b - 1, max(0, int(rng.gauss(cy, sigma))))
        p = Point([x, y])
        mm.setdefault(p, []).append((f"d_{x}_{y}").encode())
    return mm


# ---------------------------------------------------------------------------
# 1. Interactive scheme: precision recovered vs non-interactive Hilbert SRC
# ---------------------------------------------------------------------------
def interactive_precision(bits_range=range(3, 7), n_points=350, n_queries=50):
    rng = random.Random(SEED)
    xs, p_inter_src, p_inter_brc, p_nonint, tok_r1, tok_r2 = [], [], [], [], [], []
    for bits in bits_range:
        print(f"[interactive] bits={bits}")
        mm = sparse_2d(bits, n_points, rng)

        def eng():
            return EMMEngine([bits, bits], 2)

        isrc = InteractiveSRCHilbert(eng(), single_range_cover_round2=True)
        k1 = isrc.setup(16)
        isrc.build_index(k1, mm)
        ibrc = InteractiveSRCHilbert(eng(), single_range_cover_round2=False)
        k2 = ibrc.setup(16)
        ibrc.build_index(k2, mm)
        ni = TdagSRCHilbert(eng())
        k3 = ni.setup(16)
        ni.build_index(k3, mm)
        qs = rects(bits, n_queries, rng)
        ps, pb, pn, t1, t2 = [], [], [], [], []
        for q in qs:
            tp = true_positives(q, mm)
            g = isrc.query(k1, q)
            assert tp.issubset(g)
            if g:
                ps.append(len(tp) / len(g))
            t1.append(isrc.last_tokens_round1)
            t2.append(isrc.last_tokens_round2)
            gb = ibrc.query(k2, q)
            assert tp.issubset(gb)
            if gb:
                pb.append(len(tp) / len(gb))
            gn = ni.resolve(k3, ni.search(ni.trapdoor(k3, q)))
            if gn:
                pn.append(len(tp) / len(gn))
        xs.append(2 * bits)
        p_inter_src.append(st.mean(ps))
        p_inter_brc.append(st.mean(pb))
        p_nonint.append(st.mean(pn))
        tok_r1.append(st.mean(t1))
        tok_r2.append(st.mean(t2))

    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    ax.plot(xs, p_nonint, "-o", color=C_BASE, label="non-interactive TdagSRCHilbert (1 round)")
    ax.plot(xs, p_inter_src, "--s", color=C_NEW, label="interactive, SRC round 2 (2 rounds)")
    ax.plot(xs, p_inter_brc, "-.D", color=C_THIRD, label="interactive, BRC round 2 (2 rounds)")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("Domain size  (log$_2$ |domain|)")
    ax.set_ylabel("Avg. precision")
    ax.set_title("Interaction recovers precision lost to Hilbert SRC")
    ax.legend()
    save(fig, "fig_interactive_precision")

    fig, ax = plt.subplots(figsize=(6.6, 4.3))
    ax.bar(xs, tok_r1, width=0.8, color=C_BASE, label="round 1 (metadata)")
    ax.bar(xs, tok_r2, width=0.8, bottom=tok_r1, color=C_NEW, label="round 2 (documents)")
    ax.set_xlabel("Domain size  (log$_2$ |domain|)")
    ax.set_ylabel("Avg. # search tokens")
    ax.set_title("Interactive scheme: tokens per round (2 communication rounds)")
    ax.legend()
    save(fig, "fig_interactive_tokens")
    return dict(xs=xs, p_inter_src=p_inter_src, p_inter_brc=p_inter_brc, p_nonint=p_nonint, tok_r1=tok_r1, tok_r2=tok_r2)


# ---------------------------------------------------------------------------
# 2. Hilbert R-tree vs RangeBRCHilbert
# ---------------------------------------------------------------------------
def rtree_vs_binary(bits_range=range(3, 8), n_points=800, n_queries=60, capacity=4):
    rng = random.Random(SEED + 2)
    xs, tok_rt, tok_brc, idx_rt, idx_brc, prec_rt = [], [], [], [], [], []
    for bits in bits_range:
        print(f"[rtree] bits={bits}")
        mm = sparse_2d(bits, n_points, rng)
        rt = HilbertRTreeScheme(EMMEngine([bits, bits], 2), node_capacity=capacity)
        k = rt.setup(16)
        rt.build_index(k, mm)
        brc = RangeBRCHilbert(EMMEngine([bits, bits], 2))
        k2 = brc.setup(16)
        brc.build_index(k2, mm)
        qs = rects(bits, n_queries, rng)
        tr, tb, pr = [], [], []
        for q in qs:
            tp = true_positives(q, mm)
            td = rt.trapdoor(k, q)
            got = rt.resolve(k, rt.search(td))
            assert tp.issubset(got)
            tr.append(len(td))
            pr.append(len(tp) / len(got) if got else 1.0)
            tb.append(len(brc.trapdoor(k2, q)))
        xs.append(2 * bits)
        tok_rt.append(st.mean(tr))
        tok_brc.append(st.mean(tb))
        prec_rt.append(st.mean(pr))
        assert rt.encrypted_db is not None and brc.encrypted_db is not None
        idx_rt.append(sum(sys.getsizeof(a) + sys.getsizeof(b) for a, b in rt.encrypted_db.items()) / 1024)
        idx_brc.append(sum(sys.getsizeof(a) + sys.getsizeof(b) for a, b in brc.encrypted_db.items()) / 1024)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.3))
    a1.plot(xs, tok_brc, "-o", color=C_BASE, label="RangeBRCHilbert (binary tree)")
    a1.plot(xs, tok_rt, "--s", color=C_NEW, label="Hilbert R-tree (packed)")
    a1.set_xlabel("Domain size  (log$_2$ |domain|)")
    a1.set_ylabel("Avg. # search tokens")
    a1.set_title("Query leakage: search tokens")
    a1.legend()
    a2.plot(xs, idx_brc, "-o", color=C_BASE, label="RangeBRCHilbert")
    a2.plot(xs, idx_rt, "--s", color=C_NEW, label="Hilbert R-tree")
    a2.set_yscale("log")
    a2.set_xlabel("Domain size  (log$_2$ |domain|)")
    a2.set_ylabel("Encrypted index size (KiB, log)")
    a2.set_title("Storage: encrypted index size")
    a2.legend()
    fig.tight_layout()
    save(fig, "fig_rtree")
    return dict(xs=xs, tok_rt=tok_rt, tok_brc=tok_brc, idx_rt=idx_rt, idx_brc=idx_brc, prec_rt=prec_rt)


# ---------------------------------------------------------------------------
# 3. Data-dependent (density) vs uniform indexing on skewed data
# ---------------------------------------------------------------------------
def datadependent_vs_uniform(bits=7, n_points=1500, n_queries=80):
    rng = random.Random(SEED + 4)
    mm = clustered_2d(bits, n_points, rng)
    uni = RangeBRC(EMMEngine([bits, bits], 2))
    k = uni.setup(16)
    uni.build_index(k, mm)
    dep = RangeBRCDataDependent(EMMEngine([bits, bits], 2))
    k2 = dep.setup(16)
    dep.build_index(k2, mm)
    qs = rects(bits, n_queries, rng)
    tok_u, tok_d = [], []
    for q in qs:
        tok_u.append(len(uni.trapdoor(k, q)))
        tok_d.append(len(dep.trapdoor(k2, q)))
    assert uni.encrypted_db is not None and dep.encrypted_db is not None
    idx_u = sum(sys.getsizeof(a) + sys.getsizeof(b) for a, b in uni.encrypted_db.items()) / 1024
    idx_d = sum(sys.getsizeof(a) + sys.getsizeof(b) for a, b in dep.encrypted_db.items()) / 1024
    print(f"[datadep] tokens uniform={st.mean(tok_u):.2f} dependent={st.mean(tok_d):.2f}; index uniform={idx_u:.0f} KiB dependent={idx_d:.0f} KiB")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.5, 4.3))
    a1.bar(["uniform\nRangeBRC", "density\nRangeBRC"], [st.mean(tok_u), st.mean(tok_d)], color=[C_BASE, C_NEW])
    a1.set_ylabel("Avg. # search tokens")
    a1.set_title("Query leakage on clustered data")
    a2.bar(["uniform\nRangeBRC", "density\nRangeBRC"], [idx_u, idx_d], color=[C_BASE, C_NEW])
    a2.set_ylabel("Encrypted index size (KiB)")
    a2.set_title("Storage on clustered data")
    fig.suptitle(f"Data-dependent (density) vs. uniform indexing, clustered 2$^{{{2 * bits}}}$ domain", y=1.02)
    fig.tight_layout()
    save(fig, "fig_datadependent")
    return dict(tok_uniform=st.mean(tok_u), tok_dependent=st.mean(tok_d), idx_uniform=idx_u, idx_dependent=idx_d)


# ---------------------------------------------------------------------------
# 4. Real dataset (Spitz phone-location trace): the two winning schemes
# ---------------------------------------------------------------------------
def real_dataset(records_limit=8000, n_queries=80):
    """
    The two winning extensions on the Spitz phone-location trace. The R-tree (no
    full TDAG) scales to a larger domain than the mid-overlap TDAG schemes, so the
    two panels use independent, tractable bit ranges.
    """
    rng = random.Random(SEED + 7)

    def load(bits):
        raw = generate_spitz(bits, records_limit)
        return {Point(list(t)): raw[t] for t in raw}

    # Panel A: R-tree vs RangeBRCHilbert (tokens), bits 5..7.
    xa, tok_rt, tok_brc = [], [], []
    for bits in (5, 6, 7):
        mm = load(bits)
        print(f"[real A] Spitz bits={bits}: {len(mm)} pts, {sum(len(v) for v in mm.values())} recs")
        rt = HilbertRTreeScheme(EMMEngine([bits, bits], 2))
        k = rt.setup(16)
        rt.build_index(k, mm)
        brc = RangeBRCHilbert(EMMEngine([bits, bits], 2))
        kb = brc.setup(16)
        brc.build_index(kb, mm)
        qs = rects(bits, n_queries, rng)
        tr = [len(rt.trapdoor(k, q)) for q in qs]
        tb = [len(brc.trapdoor(kb, q)) for q in qs]
        xa.append(2 * bits)
        tok_rt.append(st.mean(tr))
        tok_brc.append(st.mean(tb))
        print(f"          tokens R-tree={st.mean(tr):.1f} BRC={st.mean(tb):.1f}")

    # Panel B: interactive vs non-interactive (precision), bits 4..6 (mid-overlap TDAG).
    xb, p_inter, p_nonint = [], [], []
    for bits in (4, 5, 6):
        mm = load(bits)
        print(f"[real B] Spitz bits={bits}: {len(mm)} pts")
        isrc = InteractiveSRCHilbert(EMMEngine([bits, bits], 2))
        ki = isrc.setup(16)
        isrc.build_index(ki, mm)
        ni = TdagSRCHilbert(EMMEngine([bits, bits], 2))
        kn = ni.setup(16)
        ni.build_index(kn, mm)
        pi, pn = [], []
        for q in rects(bits, n_queries, rng):
            tp = true_positives(q, mm)
            if not tp:
                continue
            gi = isrc.query(ki, q)
            assert tp.issubset(gi)
            pi.append(len(tp) / len(gi) if gi else 1.0)
            gn = ni.resolve(kn, ni.search(ni.trapdoor(kn, q)))
            pn.append(len(tp) / len(gn) if gn else 1.0)
        xb.append(2 * bits)
        p_inter.append(st.mean(pi))
        p_nonint.append(st.mean(pn))
        print(f"          precision interactive={st.mean(pi):.3f} non-int={st.mean(pn):.3f}")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11.5, 4.3))
    a1.plot(xa, tok_brc, "-o", color=C_BASE, label="RangeBRCHilbert")
    a1.plot(xa, tok_rt, "--s", color=C_NEW, label="Hilbert R-tree")
    a1.set_xlabel("Domain size  (log$_2$ |domain|)")
    a1.set_ylabel("Avg. # search tokens")
    a1.set_title("R-tree: fewer tokens on real data")
    a1.legend()
    a2.plot(xb, p_nonint, "-o", color=C_BASE, label="non-interactive TdagSRCHilbert")
    a2.plot(xb, p_inter, "--s", color=C_NEW, label="interactive (SRC round 2)")
    a2.set_ylim(0, 1.05)
    a2.set_xlabel("Domain size  (log$_2$ |domain|)")
    a2.set_ylabel("Avg. precision")
    a2.set_title("Interaction: better precision on real data")
    a2.legend()
    fig.suptitle("The two winning extensions on the Spitz phone-location trace (real 2D data)", y=1.02)
    fig.tight_layout()
    save(fig, "fig_real_dataset")
    return dict(xa=xa, tok_rt=tok_rt, tok_brc=tok_brc, xb=xb, p_inter=p_inter, p_nonint=p_nonint)


if __name__ == "__main__":
    data = {}
    print("== 1. Interactive double-index ==")
    data["interactive"] = interactive_precision()
    print("== 2. Hilbert R-tree ==")
    data["rtree"] = rtree_vs_binary()
    print("== 3. Data-dependent / density ==")
    data["datadependent"] = datadependent_vs_uniform()
    print("== 4. Real dataset (Spitz) ==")
    data["real"] = real_dataset()
    with open(os.path.join(OUT, "future_data.json"), "w") as f:
        json.dump(data, f, indent=2)
    print("Done. Figures + future_data.json in", OUT)
