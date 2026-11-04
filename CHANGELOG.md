# Changelog

All notable changes to this project are documented here.

## [1.2.0] — Shared scheme core, true TDAGs, corrected 3D data

### Fixed

- **The TDAG was built as a tree with duplicated cousin subtrees, not as a
  DAG.** `HyperRangeTree.init` recursively re-divided every mid-overlap cousin,
  so a cousin's halves (which are the halves of its two neighbours) were built
  again as fresh subtrees: at a `2^10` domain the structure had 68,890 nodes
  for 3,060 distinct canonical ranges, and `descend` returned 127 ranges (20
  distinct) per point. Every record was therefore indexed several times under
  the *same* label, inflating index size, build time and result counts of
  every TDAG-based scheme (`tdag_src*`, both `interactive_src*` indices) by a
  factor growing with the domain — the gigabyte-sized TDAG indices and the
  "~2^12 wall" of earlier reports were artefacts. Identical ranges are now
  built once and shared (the DAG of Falzon et al.), and `descend`/`rc`/`src`
  visit each node once. Token counts and precision of earlier reports were
  not affected; their index sizes and result counts were. The TDAG and
  interactive benchmarks were re-run.
- **`nh_64` was loaded with float coordinates** (`2.0` instead of `2`), so the
  Linear scheme's labels (serialised coordinates) never matched the integer
  queries: its 3D report showed `0` results for every query. Coordinates are
  parsed as integers; the report was regenerated.
- The EMM engine encoded the postings-list position as `bytes(i)` — `i` zero
  bytes — making the `i`-th lookup cost `O(i)` and a long postings list
  quadratic. The counter is now a fixed-width 8-byte integer.
- `cli.get_dataset` raised `NameError` instead of its "unknown dataset" error.
- `HilbertScheme.search` silently returned an empty set before
  `build_index`; every scheme now raises `ValueError("Index is not built yet!")`.
- `Scaler.upscale` assumed two dimensions (`bits * 2`); it now takes the
  dimension count. The class remains experimental and is not used by any scheme.
- The per-dimension projection used by the data-dependent *product* builders
  kept only the records of the last point sharing a coordinate; records are
  now merged per axis value (no effect on the benchmarked cell weighting).

### Changed — performance

- `HyperRangeTree.rc` (the Best Range Cover) no longer expands vertices that
  are disjoint from the query. The cover is unchanged (pinned by a test) but
  the traversal is `O(|cover| · height)` instead of a full walk of the
  structure: a 3D query of `range_brc_hilbert` on `nh_64` (a `2^18`-cell
  curve, ~1 000 segments per box) dropped from ~350 s to 0.3 s, which is what
  made the 3D Hilbert range-tree benchmarks possible.

### Changed — architecture

- **One scheme core.** All tree-based schemes are now `StructuredScheme`
  subclasses: a scheme is a *structure builder* (`_build_structure`) plus a
  *cover rule* (`BestRangeCover` / `SingleRangeCover`); Hilbert variants add a
  projection (`HilbertScheme`). `build_index`, `trapdoor` and `search` are
  written once. The 16 structured scheme files shrank from ~100 lines of
  copy-pasted protocol each to a docstring and a one-line builder; the
  structure constructors live in `ers.schemes.common.structure_builders`.
- **One packed R-tree.** `PackedRTree` holds the node type, level packing,
  cover algorithm and traversal; `HilbertRTree` and `STRRTree` only supply the
  leaf order. `PackedRTreeScheme` holds the scheme; `HilbertRTreeScheme` /
  `RTreeScheme` only supply the tree.
- `EMM` gained `encrypted_db`, the shared `search`, and an `exact` class
  attribute declaring whether a scheme can return false positives; the
  benchmark harness measures precision from that flag instead of an
  `isinstance` whitelist.
- `HyperRangeTreeProduct.descend` takes a `HyperRange` (a point range), like
  `HyperRangeTree.descend`.
- `InteractiveSRC.search(trapdoors, index)` is now `search_index`; the
  single-round `search` raises `NotImplementedError` pointing at `query`.
- The harness falls back to sequential in-process query execution when the
  scheme cannot be pickled for the process pool (deep data-dependent trees over
  large domains raise `RecursionError` in the pickler); it shares one metric-writing path between the single-round and
  the interactive driver (`write_bucket_averages`, `measure_precision`).

### Added

- **Explicit mass weighting for data-dependent dividers.** The dividers
  balance *occupied cells* (every distinct point once), which is what every
  benchmark measured and which reduces to the uniform cut on fully occupied
  domains (e.g. the per-attribute marginals of cali, where `range_brc` and
  `range_brc_data_dependent` build identical trees). This is now spelled out
  and selectable: `weight="cells"` (default) or `weight="records"` (balance
  records, the probability-based notion) on every data-dependent divider and
  on `data_dependent_tree` / `data_dependent_tree_product`.
- **Record-weighted scheme variants** `*_data_dependent_records` (8 CLI
  names): the data-dependent schemes with `mass_weight = "records"`, so the
  two weightings can be benchmarked side by side. The report site and the
  figure script mark them with a square marker.
- **`lean/` — Lean 4 formalisation** of the paper's results: the segment
  decomposition lemma, the quadtree equivalence (abstract) with
  `decide`-checked curve properties, the range-tree strict-subset
  proposition, the divider termination / single-cover lemma (with the uniform
  divider as a witness that its hypotheses are satisfiable), and a geometric
  bridge lemma deriving the segment lemma's boundary hypotheses from curve
  adjacency. Builds with core Lean only (`cd lean && lake build`);
  `tests/test_lean_agreement.py` pins the Lean model to the implementation.
- `scripts/validate_reports.py` — checks every report against the contract
  of its scheme (one token for single covers and for round one of the
  interactive protocol, exact schemes agreeing on result counts to the record,
  the provable equivalences holding to the byte, index-size orderings, a
  shared workload, no false negatives) and, with `--replay`, rebuilds every
  scheme on the real dataset to recompute the workload and reproduce the
  report per query.
- `scripts/gen_report_figures.py` — every figure and table of the paper's
  evaluation, generated from the `.xlsx` reports (PDF + PNG + LaTeX tables +
  a flat `summary.csv`), with the same visual encoding as the report site.
- `pyproject.toml` now declares the package (`pip install -e ".[dev]"`).
- Tests: `tests/test_registry.py` runs every CLI-registered scheme end-to-end
  (no false negatives, declared exactness, single-token SRC, 3D NH integer
  coordinates); `tests/test_emm_engine.py` pins the engine round-trip.
- Module docstrings for every module that lacked one; descriptive error
  messages instead of `print` + bare `raise`.

## [1.1.0] — Completing the design-space matrix

### Added — schemes

Every sensible cell of the structure × cover × domain × divider design space is
now implemented (see the matrix in the README):

- **`tdag_src_data_dependent` / `tdag_src_hilbert_data_dependent`** — the
  data-dependent TDAGs, powered by a new
  `DataDependentSplitMidOverlapDivider` that places both the CDF-balanced cut
  points *and* the mid-overlap "cousin" nodes by point mass (the cousin spans
  the mass-median of one chunk to the mass-median of the next — the quartile
  picture of the uniform TDAG transplanted from length-space to mass-space).
  SRC's single-token guarantee is preserved.
- **`interactive_src`** (`InteractiveSRCNative`) — the two-round
  `Logarithmic-SRC-i` protocol on the native multi-dimensional grid:
  lexicographic-rank document order, product-TDAG round one (the exact
  interactive upgrade of `tdag_src`). `InteractiveSRC` gained overridable
  value-domain hooks so all three variants (1-D, Hilbert, native) share one
  protocol implementation.
- **`rtree`** (`RTreeScheme` / `STRRTree`) — the native packed R-tree:
  Sort-Tile-Recursive bulk loading over the same MBR node type and cover
  algorithm as `hilbert_rtree`, isolating the contribution of the packing
  order (curve vs. axis tiling).

### Fixed

- **`RangeBRCDataDependent` adapted every dimension to dimension 0's
  marginal**: all per-dimension trees received the full multi-dimensional
  multi-map, and the 1-D density filter silently compared coordinate 0 for
  every axis. Each tree now receives the points projected onto its own
  dimension. (The new TDAG data-dependent schemes were written with the
  projection from the start.)
- The benchmark CLI raises Python's recursion limit: on heavily clustered
  data, mass-balanced binary splits legitimately produce trees as deep as the
  domain is long (a finite chain, one cell per level), which overflowed the
  default limit of 1000 on real datasets (cali at domain ≥ 2^6).

### Changed — performance

- `CustomDataDependentSplitDivider` gained a sorted-array/bisect fast path for
  1-D dividers (every per-dimension and Hilbert-domain tree): each node's
  density histogram now touches only the points inside the node instead of
  rescanning the whole dataset, turning deep data-dependent builds from
  O(points × nodes) into O(points × depth).

### Changed — tooling & layout

- All runnable scripts moved from the repository root into **`scripts/`**;
  the per-dataset wrappers now source `scripts/lib/common.sh`, which anchors
  them at the repo root, picks the `.venv` interpreter, and validates the
  scheme argument against the CLI registry — the single source of truth,
  replacing six hand-copied scheme lists. `run_all.sh <dataset> [scheme ...]`
  batch-runs any subset (default: every registered scheme).
- The Dash dashboard was rebuilt as a **multi-page report site**
  (`python3 -m ers.benchmark.plot.plot_benchmarks benchmarks`): an Overview
  page documenting the EMM pipeline and every metric, a Scheme-guide page with
  the design-space matrix and per-family cards, the Explorer plot, and a
  Coverage page showing which reports exist. Plots use a colorblind-validated
  taxonomy encoding — hue = scheme family, dashed = Hilbert, diamond =
  data-dependent — so colors never reshuffle as the selection changes.

### Added — tests

- `tests/test_new_schemes.py`: divider invariants (chunk coverage, seam
  cousins, termination on clustered data), single-token + no-false-negative
  checks for both data-dependent TDAGs (2D and 3D), the native interactive
  protocol (including exactness with a BRC second round and the rank-codec
  bijection), STR R-tree packing/cover soundness, and a regression test
  pinning the per-dimension marginal fix.

### Changed — type-safety & IDE hygiene

- The codebase now passes **pyright (basic)** with zero errors, alongside
  ruff lint/format; both are configured in `pyproject.toml` so VS Code /
  Pylance picks up the same settings and the project virtualenv.
- Every scheme's lazily-built state (`tree` / `tree_product` / `tdag` /
  `encrypted_db`, the interactive indices) is annotated `Optional` and
  guarded: calling `trapdoor()`/`search()` before `build_index()` now raises
  a clear `ValueError("Index is not built yet!")` instead of crashing with
  `AttributeError` on `None`.
- `HyperRangeDivider.divide` is properly abstract (`NotImplementedError`);
  the fixed-fanout dividers accept `Optional` per-dimension lists and name
  their override parameters consistently.
- `BytesToObject` is typed `Any` (the caller knows the serialized shape);
  precision fixes: the harness measures precision for **all** schemes that
  can return false positives — the whitelist previously omitted both packed
  R-trees and the data-dependent TDAGs — and the report site renders the
  "-1 = exact by construction" sentinel as the 1.0 it means (never mapping
  the false-negative `-inf` marker).
- `plot_hilbert.py` (the interactive Hilbert-curve/cover inspector) moved
  from `ers/benchmark/plot/` to `scripts/`, with all runnable entry points.

## [1.0.0] — Range Search on Encrypted Multi-Attribute Data

First tagged release: a dimension-generic framework for range search over
encrypted multi-attribute data, the Hilbert-curve schemes, and an honest
evaluation of when they help. Accompanied by a technical report.

### Added — future-work schemes

These realise three of the directions identified in the report's discussion and
are benchmarked in [`gen_future_figures.py`](gen_future_figures.py):

- **Interactive double-index scheme** (`InteractiveSRC`, `InteractiveSRCHilbert`) —
  the two-round `Logarithmic-SRC-i` construction of Demertzis et al. A first index
  maps the (Hilbert) value domain to compact document-index ranges; the client
  filters false positives locally, then a second index returns the documents.
  Restores precision from ~0.25 to ~0.75 (SRC round two) or exactly 1.0 (BRC round
  two) versus the non-interactive Hilbert SRC, for one extra communication round
  plus client-side state.
- **Packed Hilbert R-tree** (`HilbertRTree`, `HilbertRTreeScheme`; CLI name
  `hilbert_rtree`) — a data-dependent range-supporting structure that bulk-loads
  points in Hilbert order. Cuts search tokens (~108 → ~23 at a 2^14 domain) and
  index size (~3x) versus the binary-tree `RangeBRCHilbert`, with the advantage
  widening as the domain grows.
- Density- / probability-based indexing was already present (the
  `data_dependent` schemes); it is now benchmarked, with the honest finding that
  it can *hurt* axis-aligned range queries unless the queries are data-dependent
  too.

### Added — tooling

- `hilbert_rtree` and `interactive_src_hilbert` are registered in the CLI and the
  dataset run scripts, so they can be benchmarked like any other scheme.
- The interactive scheme emits dashboard-compatible reports via a dedicated
  `run_interactive_benchmark` (with `trapdoor_count_round1` /
  `trapdoor_count_round2` sheets), so it can be **compared against the
  single-round schemes** in the Dash dashboard
  (`python3 -m ers.benchmark.plot.plot_benchmarks benchmarks`).

### Added — quality

- A `pytest` test suite under [`tests/`](tests/) pinning the core invariants:
  no false negatives for every scheme in 2D and 3D, exactness of the tolerance-0
  Hilbert cover, `boundary_points` surface completeness, and the precision / token
  advantages of the interactive and R-tree schemes. Independently
  cross-validated (brute-force ground truth, exact crypto round-trip, payload
  uniqueness) — all checks pass.
- Figure-generation scripts `gen_figures.py` and `gen_future_figures.py` that
  reproduce every figure in the report and README from the real code.
- Docstrings and inline algorithm comments across the whole `ers` package.
- README illustrated with generated figures and a Future-work section.

### Fixed

- **Critical:** `HyperRange.boundary_points()` returned only the *edges* of a
  query box, not its full surface, dropping face-interior cells in 3D and causing
  false negatives in every Hilbert scheme. It now returns the complete surface.
- `Scaler.downscale` used incorrect (`half + val % half`) arithmetic; replaced
  with a correct coordinate right-shift.
- The benchmark dashboard (`plot_benchmarks.py`) parsed multi-token dataset names
  (`nh_64`, `dense_3d`, `random_2d`) incorrectly and used the obsolete
  `app.run_server`; both fixed.
- `benchmark.py` raised `KeyError` when a query bucket was empty.
- `cali.sh` had stray Python source appended to it.

### Changed

- `requirements.txt` relaxed from exact, stale pins to minimum bounds that
  install cleanly on Python 3.12–3.14 (NumPy 2.x, pandas 3.x, dash 3.x).

### Notes

This repository implements cryptographic primitives for **research purposes
only**; do not use them in production. Licensed under Apache 2.0.
