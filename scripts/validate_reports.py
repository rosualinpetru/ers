#!/usr/bin/env python3
"""
Validate the benchmark reports against the contract of every scheme.

Reads the ``.xlsx`` reports (latest per scheme × dataset × domain) and checks
properties that must hold by construction, independently of the workload:

* **single range covers** issue exactly one token in every bucket;
* **interactive** schemes issue exactly one token in round one, and the total
  equals the sum of the rounds;
* **exact schemes** carry the "exact" precision sentinel and return exactly
  the same number of results as every other exact scheme on the same
  (dataset, domain, bucket) -- they all return the true positives and nothing
  else, so their result counts must agree to the record;
* **lossy schemes** never return fewer results than the exact ones, their
  precision lies in ``[0, 1]`` and no bucket records a false negative;
* **provable equivalences** hold to the byte: ``linear == linear_hilbert``,
  ``quad_brc == quad_brc_hilbert`` and ``quad_src == quad_src_hilbert`` in
  tokens, results and index size;
* **structural orderings** of index size: a TDAG product stores at least as
  much as the range-tree product, which stores at least as much as the
  quadtree, which stores at least as much as the linear index;
* the **workload is shared**: the linear scheme's token count (one per query
  cell) is identical across datasets with the same (dimensions, domain).

With ``--replay DATASET BITS`` the validator additionally **re-executes** every
scheme that has a report for that configuration: it rebuilds the index on the
real dataset, runs the cached workload, and checks per query that no true
positive is dropped, that exact schemes return exactly the true positives,
that single covers issue one token, and that the recomputed bucket means
reproduce the report (tokens and precision are deterministic for every scheme
but the interactive ones, whose random tie-breaking of equal values is allowed
a small tolerance). The reports only hold bucket means, so this is the only
way to check per-query properties.

Usage::

    python3 scripts/validate_reports.py [--benchmarks benchmarks] [--replay dense_2d 4] [--replay cali 5]

Exit status is non-zero when any check fails.
"""

import argparse
import os
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from scripts.gen_report_figures import Reports  # noqa: E402

SRC_SCHEMES = {s for s in ("quad_src", "tdag_src", "quad_src_hilbert", "tdag_src_hilbert")} | {
    f"{s}_data_dependent{r}" for s in ("quad_src", "tdag_src", "quad_src_hilbert", "tdag_src_hilbert") for r in ("", "_records")
}
EXACT_SCHEMES = {"linear", "linear_hilbert", "range_brc", "quad_brc", "range_brc_hilbert", "quad_brc_hilbert"} | {
    f"{s}_data_dependent{r}" for s in ("range_brc", "quad_brc", "range_brc_hilbert", "quad_brc_hilbert") for r in ("", "_records")
}
INTERACTIVE = {"interactive_src", "interactive_src_hilbert"}
EQUIVALENT = [("linear", "linear_hilbert"), ("quad_brc", "quad_brc_hilbert"), ("quad_src", "quad_src_hilbert")]
STORAGE_ORDER = ["tdag_src", "range_brc", "quad_brc", "linear"]  # non-increasing index size


class Checker:
    def __init__(self):
        self.failures: List[str] = []
        self.passed = 0

    def check(self, ok: bool, msg: str):
        if ok:
            self.passed += 1
        else:
            self.failures.append(msg)


def replay(R: Reports, C: Checker, dataset: str, bits: int) -> None:
    """Rebuild every reported scheme on ``dataset`` at ``bits`` and recompute the workload."""
    import math
    import statistics as st

    from ers.benchmark.benchmark import BUCK_SIZE, PRECISION_FALSE_NEGATIVE, generate_query_bucks, measure_precision
    from ers.benchmark.cli import INTERACTIVE_SCHEMES, get_dataset, schemes
    from ers.schemes.common.emm_engine import EMMEngine

    sys.setrecursionlimit(1_000_000)
    ds, dims = get_dataset(dataset, bits, 10**6)
    bucks = generate_query_bucks(20, dims, bits)
    tag = f"replay {dataset} {dims}D 2^{dims * bits}"
    print(f"\n== {tag}: {sum(len(v) for v in bucks.values())} queries, {len(ds)} points ==")
    for name in sorted(schemes):
        if (name, dataset, dims, bits) not in R.data:
            continue
        scheme = schemes[name](EMMEngine([bits] * dims, dims))
        key = scheme.setup(16)
        scheme.build_index(key, ds)
        tokens: Dict[int, List[int]] = defaultdict(list)
        precision: Dict[int, List[float]] = defaultdict(list)
        for tb in range(0, 99, BUCK_SIZE):
            for q in bucks.get(tb, []):
                if name in INTERACTIVE_SCHEMES:
                    docs, m = scheme.query_with_metrics(key, q)
                    n_tokens = m["trapdoor_count"]
                else:
                    td = scheme.trapdoor(key, q)
                    docs = scheme.resolve(key, scheme.search(td))
                    n_tokens = len(td)
                p = measure_precision(q, ds, docs)
                C.check(p != PRECISION_FALSE_NEGATIVE, f"[{tag}] {name}: false negative on {q}")
                if scheme.exact:
                    C.check(p == 1.0, f"[{tag}] {name}: declared exact but precision {p:.3f} on {q}")
                if name in SRC_SCHEMES:
                    C.check(n_tokens == 1, f"[{tag}] {name}: {n_tokens} tokens on {q}")
                tokens[tb].append(n_tokens)
                precision[tb].append(p)
        rep_tokens = R.buckets(name, dataset, dims, bits, "trapdoor_count")
        rep_prec = R.buckets(name, dataset, dims, bits, "precision")
        tok_tol, prec_tol = (3, 0.1) if name in INTERACTIVE_SCHEMES else (0, 1e-9)
        for tb, vals in tokens.items():
            got = math.floor(st.mean(vals))
            C.check(abs(got - rep_tokens.get(tb, -1)) <= tok_tol, f"[{tag}] {name} bucket {tb}: report says {rep_tokens.get(tb)} tokens, replay gives {got}")
            if not scheme.exact:
                got_p = st.mean(precision[tb])
                C.check(abs(got_p - rep_prec.get(tb, -1)) <= prec_tol, f"[{tag}] {name} bucket {tb}: report precision {rep_prec.get(tb)}, replay {got_p:.4f}")
        print(f"  {name}: reproduced ({len(tokens)} buckets)")


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n\n")[0])
    ap.add_argument("--benchmarks", default=os.path.join(REPO_ROOT, "benchmarks"))
    ap.add_argument("--replay", nargs=2, action="append", metavar=("DATASET", "BITS"), default=[], help="re-execute every scheme on this configuration")
    args = ap.parse_args()

    R = Reports(args.benchmarks)
    C = Checker()
    configs = sorted({(d, dims, b) for (_, d, dims, b) in R.data})
    print(f"{len(R.data)} reports, {len(configs)} (dataset, dims, domain) configurations\n")

    for dataset, dims, bits in configs:
        tag = f"{dataset} {dims}D 2^{dims * bits}"
        present = {s for (s, d, dd, b) in R.data if (d, dd, b) == (dataset, dims, bits)}

        # --- single range covers: exactly one token -------------------------
        for s in present & SRC_SCHEMES:
            toks = R.buckets(s, dataset, dims, bits, "trapdoor_count")
            C.check(bool(toks) and all(v == 1 for v in toks.values()), f"[{tag}] {s}: SRC must issue 1 token per query, got {toks}")

        # --- interactive: round one is one token, rounds add up -------------
        for s in present & INTERACTIVE:
            r1 = R.buckets(s, dataset, dims, bits, "trapdoor_count_round1")
            r2 = R.buckets(s, dataset, dims, bits, "trapdoor_count_round2")
            tot = R.buckets(s, dataset, dims, bits, "trapdoor_count")
            C.check(bool(r1) and all(v == 1 for v in r1.values()), f"[{tag}] {s}: round one must be 1 token, got {r1}")
            C.check(all(abs(tot[k] - (r1[k] + r2[k])) <= 1 for k in tot), f"[{tag}] {s}: total tokens != round1 + round2")

        # --- exact schemes: sentinel + identical result counts --------------
        exact_counts: Dict[int, Dict[str, float]] = defaultdict(dict)
        for s in present & EXACT_SCHEMES:
            sheets = R.data[(s, dataset, dims, bits)]
            if "precision" in sheets and any(b is not None for b in sheets["precision"]):
                raw = {b: v for b, v in sheets["precision"].items() if b is not None}
                C.check(all(v == -1 for v in raw.values()), f"[{tag}] {s}: exact scheme must record the exact sentinel, got {raw}")
            for b, v in R.buckets(s, dataset, dims, bits, "search_count").items():
                exact_counts[b][s] = v
        truth: Dict[int, Optional[float]] = {}
        for b, by_scheme in exact_counts.items():
            vals = set(by_scheme.values())
            C.check(len(vals) == 1, f"[{tag}] bucket {b}: exact schemes disagree on the result count: {by_scheme}")
            truth[b] = next(iter(vals)) if len(vals) == 1 else None

        # --- lossy schemes: superset, precision consistent -----------------
        for s in present - EXACT_SCHEMES:
            prec = R.buckets(s, dataset, dims, bits, "precision")
            raw = R.data[(s, dataset, dims, bits)].get("precision", {})
            C.check(all(v != float("-inf") for v in raw.values()), f"[{tag}] {s}: a bucket recorded a false negative")
            C.check(all(0 <= v <= 1 for v in prec.values()), f"[{tag}] {s}: precision outside [0, 1]: {prec}")
            counts = R.buckets(s, dataset, dims, bits, "search_count")
            for b, n in counts.items():
                tp = truth.get(b)
                if tp is not None:
                    C.check(n + 1 >= tp, f"[{tag}] {s} bucket {b}: returned {n} results but the true positives number {tp}")

        # --- equivalences ---------------------------------------------------
        for a, b2 in EQUIVALENT:
            if a in present and b2 in present:
                for metric in ("trapdoor_count", "search_count"):
                    C.check(
                        R.buckets(a, dataset, dims, bits, metric) == R.buckets(b2, dataset, dims, bits, metric), f"[{tag}] {a} and {b2} must agree on {metric}"
                    )
                C.check(
                    R.scalar(a, dataset, dims, bits, "index_size") == R.scalar(b2, dataset, dims, bits, "index_size"),
                    f"[{tag}] {a} and {b2} must have equal index size",
                )

        # --- storage ordering ----------------------------------------------
        sizes = [(s, R.scalar(s, dataset, dims, bits, "index_size")) for s in STORAGE_ORDER if s in present]
        for (s1, v1), (s2, v2) in zip(sizes, sizes[1:]):
            if v1 is not None and v2 is not None:
                C.check(v1 >= v2, f"[{tag}] index size of {s1} ({v1:.0f}) should be >= {s2} ({v2:.0f})")

    # --- shared workload across datasets --------------------------------------
    by_domain: Dict[Tuple[int, int], Dict[str, Dict[int, float]]] = defaultdict(dict)
    for s, d, dims, b in R.data:
        if s == "linear":
            by_domain[(dims, b)][d] = R.buckets(s, d, dims, b, "trapdoor_count")
    for (dims, b), per_ds in by_domain.items():
        vals = list(per_ds.values())
        C.check(all(v == vals[0] for v in vals), f"[{dims}D 2^{dims * b}] linear token counts differ across datasets: {per_ds}")

    for dataset, bits in args.replay:
        replay(R, C, dataset, int(bits))

    print(f"{C.passed} checks passed, {len(C.failures)} failed")
    for f in C.failures:
        print("  FAIL", f)
    return 1 if C.failures else 0


if __name__ == "__main__":
    sys.exit(main())
