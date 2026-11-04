"""
Benchmark report site.

A multi-page Dash application that renders the ``.xlsx`` benchmark reports as a
self-contained, report-style site:

* **Overview** (``/``) — what the project measures, how the EMM pipeline works,
  how to read every metric, and how the visual encoding maps schemes to marks.
* **Scheme guide** (``/schemes``) — the design-space matrix and a documentation
  card per scheme family, so a reader can interpret results without the paper.
* **Explorer** (``/explorer``) — the interactive comparison plot: any set of
  schemes, one dataset, one metric, query-size or domain-size axis.
* **Coverage** (``/coverage``) — which (scheme × dataset × domain) reports
  exist in the loaded folder, so gaps are visible instead of silent.

Visual encoding (deliberate, and stable under filtering)
--------------------------------------------------------
With 20+ schemes, one hue per scheme would be unreadable and colorblind-unsafe.
Instead the three taxonomy axes of the design space map to three visual
channels:

* **hue** = scheme *family* (linear / range / TDAG / quad-BRC / quad-SRC /
  R-tree / interactive) — a fixed 7-slot colorblind-validated palette;
* **line dash** = domain: solid for native multi-dimensional, dashed for
  Hilbert-linearised;
* **marker** = divider: circle for uniform, diamond for data-dependent
  (cell-balanced), square for data-dependent record-balanced.

Because color follows the *family* (an entity property) rather than the
selection order, changing filters never repaints surviving series.

Usage::

    python3 -m ers.benchmark.plot.plot_benchmarks benchmarks [--port 8050]
"""

import argparse
import os
import sys
from typing import Any, cast

import dash
import pandas as pd
import plotly.graph_objects as go
from dash import Input, Output, ctx, dcc, html

# --------------------------------------------------------------------------- #
# Theme tokens (light surface), from the validated reference palette.
# --------------------------------------------------------------------------- #
SURFACE = "#fcfcfb"  # chart surface
PAGE_BG = "#f9f9f7"  # page plane
INK = "#0b0b0b"  # primary ink
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRID = "#e1e0d9"
BASELINE = "#c3c2b7"
BORDER = "rgba(11,11,11,0.10)"

# Categorical slots in the validated fixed order (adjacent-pair CVD-safe).
# One hue per scheme *family*; never cycled, never re-assigned by filtering.
FAMILY_COLORS = {
    "range": "#2a78d6",  # blue
    "quad_brc": "#008300",  # green
    "quad_src": "#e87ba4",  # magenta
    "tdag": "#eda100",  # yellow
    "linear": "#1baf7a",  # aqua
    "rtree": "#eb6834",  # orange
    "interactive": "#4a3aa7",  # violet
}

FAMILY_LABELS = {
    "linear": "Linear",
    "range": "Range tree (BRC)",
    "tdag": "TDAG (SRC)",
    "quad_brc": "Quad tree (BRC)",
    "quad_src": "Quad tree (SRC)",
    "rtree": "Packed R-tree",
    "interactive": "Interactive (2-round)",
}


def parse_scheme(name: str) -> dict:
    """
    Decompose a CLI scheme name into its three taxonomy axes.

    :param name: e.g. ``"tdag_src_hilbert_data_dependent"``.
    :return: ``{"family", "hilbert", "data_dependent", "records"}`` where
        ``records`` marks the record-weighted data-dependent variants.
    """
    base = name
    records = base.endswith("_records")
    if records:
        base = base[: -len("_records")]
    dd = base.endswith("_data_dependent")
    if dd:
        base = base[: -len("_data_dependent")]
    hilbert = base == "hilbert_rtree" or base.endswith("_hilbert")
    if base == "hilbert_rtree":
        base = "rtree"
    elif base.endswith("_hilbert"):
        base = base[: -len("_hilbert")]

    family = {
        "linear": "linear",
        "range_brc": "range",
        "tdag_src": "tdag",
        "quad_brc": "quad_brc",
        "quad_src": "quad_src",
        "rtree": "rtree",
        "interactive_src": "interactive",
    }.get(base, "range")
    return {"family": family, "hilbert": hilbert, "data_dependent": dd, "records": records}


def scheme_style(name: str) -> dict:
    """Plotly line/marker style for a scheme, from its taxonomy."""
    t = parse_scheme(name)
    return {
        "color": FAMILY_COLORS[t["family"]],
        "dash": "dash" if t["hilbert"] else "solid",
        "symbol": ("square" if t["records"] else "diamond") if t["data_dependent"] else "circle",
    }


# --------------------------------------------------------------------------- #
# Metric documentation shown under the explorer chart and on the overview page.
# --------------------------------------------------------------------------- #
METRIC_DOCS = {
    "precision": "True positives ÷ all returned results. 1.0 means no false positives. "
    "Measured per query for schemes that can overshoot (SRC variants, R-trees); "
    "exact schemes (linear, BRC at tolerance 0) are precise by construction and "
    "shown as a flat 1.0 without per-query measurement.",
    "trapdoor_count": "Search tokens issued per query — the query-side leakage surface. SRC schemes issue exactly 1; BRC schemes issue one per cover node.",
    "trapdoor_count_round1": "Tokens in round one of the interactive protocol (the metadata fetch).",
    "trapdoor_count_round2": "Tokens in round two of the interactive protocol (the document fetch).",
    "index_size": "Number of encrypted (label → value) entries in the server-held index.",
    "index_time": "Wall-clock seconds to build the encrypted index.",
    "trapdoor_time": "Seconds to generate the search tokens for a query.",
    "search_time": "Seconds the server spends answering the tokens.",
    "resolve_time": "Seconds the client spends decrypting the results.",
    "search_count": "Number of encrypted values returned before client-side filtering.",
    "rounds": "Communication rounds per query (1 for standard schemes, 2 for interactive).",
    "filter_time": "Seconds the client spends filtering round-one metadata (interactive only).",
}

QUERYLESS_METRICS = {"index_size", "index_time"}

# --------------------------------------------------------------------------- #
# Scheme-family documentation cards for the guide page.
# --------------------------------------------------------------------------- #
FAMILY_DOCS = [
    {
        "family": "linear",
        "schemes": ["linear", "linear_hilbert"],
        "what": "No tree at all: every domain point is indexed on its own. A query is "
        "answered by requesting every point inside the box (native) or every "
        "point on the Hilbert segments covering the box (Hilbert).",
        "tradeoff": "Maximal token count (one per point), perfect precision, smallest possible index. The baseline every structured scheme must beat.",
    },
    {
        "family": "range",
        "schemes": ["range_brc", "range_brc_hilbert", "range_brc_data_dependent", "range_brc_hilbert_data_dependent"],
        "what": "A binary range tree per dimension (native: their product; Hilbert: one "
        "tree over the 1-D curve). Queries take the Best Range Cover: the minimal "
        "set of tree nodes exactly tiling the query.",
        "tradeoff": "Exact answers (precision 1 for native), log-many tokens. The Hilbert "
        "variant only indexes contiguous curve segments, so its cover — and "
        "leakage — differs. Data-dependent variants cut by point mass instead "
        "of length.",
    },
    {
        "family": "tdag",
        "schemes": ["tdag_src", "tdag_src_hilbert", "tdag_src_data_dependent", "tdag_src_hilbert_data_dependent"],
        "what": "A range tree augmented with mid-overlap “cousin” nodes (a TDAG), so every "
        "query is contained in a single node. Queries issue exactly one token — "
        "the Single Range Cover.",
        "tradeoff": "Minimal tokens and leakage; precision suffers because the covering "
        "node overshoots the query. Data-dependent variants place cuts and "
        "cousins by point mass, tightening the cover on skewed data.",
    },
    {
        "family": "quad_brc",
        "schemes": ["quad_brc", "quad_brc_hilbert", "quad_brc_data_dependent", "quad_brc_hilbert_data_dependent"],
        "what": "One tree that splits every dimension in half at once (2^d children per node) — a quadtree/octree. Queries take the Best Range Cover over it.",
        "tradeoff": "With uniform splits, the native and Hilbert variants build equivalent "
        "indices (the quad decomposition mirrors the curve's construction); "
        "they differ only in node representation.",
    },
    {
        "family": "quad_src",
        "schemes": ["quad_src", "quad_src_hilbert", "quad_src_data_dependent", "quad_src_hilbert_data_dependent"],
        "what": "The quadtree with a Single Range Cover: one token for the smallest quad node containing the whole query.",
        "tradeoff": "One token, but the smallest containing quad node can be up to the "
        "full domain (a query straddling the centre) — precision collapses "
        "in the worst case. The TDAG family exists to fix exactly this.",
    },
    {
        "family": "rtree",
        "schemes": ["hilbert_rtree", "rtree"],
        "what": "A packed R-tree of minimum bounding rectangles, bulk-loaded from the "
        "data: hilbert_rtree packs points in Hilbert order (Kamel–Faloutsos); "
        "rtree packs by Sort-Tile-Recursive axis tiling — no curve involved.",
        "tradeoff": "Small covers and small indices, inherently data-dependent (the tree "
        "shape is client state and leaks data distribution). False positives "
        "only from boundary leaves. Comparing the two isolates what the "
        "packing order contributes.",
    },
    {
        "family": "interactive",
        "schemes": ["interactive_src", "interactive_src_hilbert"],
        "what": "The two-round Logarithmic-SRC-i double index: round one fetches compact "
        "value→document-index metadata (one token); the client filters false "
        "positives locally; round two fetches only the surviving documents.",
        "tradeoff": "An extra round and client-side state buy near-exact precision. The "
        "native variant orders documents lexicographically; the Hilbert "
        "variant by curve distance — round-two token counts differ "
        "accordingly.",
    },
]

# --------------------------------------------------------------------------- #
# Report loading (filename convention: scheme_dataset_dim_bits_records_queries_ts).
# --------------------------------------------------------------------------- #
DATASET_TOKENS = {
    "dense_2d": ("dense", "2d"),
    "dense_3d": ("dense", "3d"),
    "random_2d": ("random", "2d"),
    "nh_64": ("nh", "64"),
    "cali": ("cali",),
    "spitz": ("spitz",),
    "gowalla": ("gowalla",),
}


def split_scheme_and_dataset(parts):
    """Split filename tokens into (scheme, dataset, tail), longest dataset first."""
    for name, tokens in sorted(DATASET_TOKENS.items(), key=lambda kv: -len(kv[1])):
        n = len(tokens)
        for i in range(len(parts) - n + 1):
            if tuple(parts[i : i + n]) == tokens:
                return "_".join(parts[:i]), name, parts[i + n :]
    raise ValueError(f"Dataset not found in parts: {parts}")


def load_all_data(root_folder: str) -> pd.DataFrame:
    """Load every ``.xlsx`` report under ``root_folder`` into one tidy frame."""
    entries = []
    for dirpath, _, filenames in os.walk(root_folder):
        for file in filenames:
            if not file.endswith(".xlsx"):
                continue
            path = os.path.join(dirpath, file)
            parts = file[:-5].split("_")
            try:
                scheme, dataset, tail = split_scheme_and_dataset(parts)
                dim, bits = int(tail[0]), int(tail[1])
                max_q, num_q = int(tail[2]), int(tail[3])

                sheets = pd.read_excel(path, header=None, sheet_name=None, engine="openpyxl")
                for metric, df in sheets.items():
                    if df.empty:
                        continue
                    if df.shape[1] >= 2:
                        df = df.iloc[:, :2]
                        df.columns = ["query_size", metric]
                        df = df.dropna()
                    elif df.shape[0] == 1 and df.shape[1] == 1:
                        df = pd.DataFrame({"query_size": [None], metric: [df.iloc[0, 0]]})
                    else:
                        continue

                    if metric == "precision":
                        # The harness writes -1 as a "not measured" sentinel
                        # for exact schemes (linear / BRC at tolerance 0),
                        # whose precision is 1 by construction — plot it as
                        # such. -inf marks a false-negative failure and must
                        # never be silently mapped; drop it so it surfaces as
                        # a gap instead of a fake data point.
                        df = df[df[metric] != float("-inf")]
                        df.loc[df[metric] == -1, metric] = 1.0

                    df["scheme"] = scheme
                    df["dataset"] = dataset
                    df["dim"] = dim
                    df["bits"] = bits
                    df["domain_size"] = 2 ** (dim * bits)
                    df["num_queries"] = num_q
                    df["max_query_size"] = max_q
                    df["metric"] = metric
                    entries.append(df)
            except Exception as e:  # tolerate foreign files in the folder
                print(f"Skipping {file}: {e}")
    return pd.concat(entries, ignore_index=True) if entries else pd.DataFrame()


# --------------------------------------------------------------------------- #
# Figure construction.
# --------------------------------------------------------------------------- #
def base_figure(title: str, xaxis_title: str, yaxis_title: str, yscale: str) -> go.Figure:
    """An empty styled figure: recessive grid, unified hover, bottom legend."""
    fig = go.Figure()
    fig.update_layout(
        title={"text": title, "font": {"size": 18, "color": INK}},
        template=None,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font={"family": 'system-ui, -apple-system, "Segoe UI", sans-serif', "color": INK_SECONDARY, "size": 14},
        hovermode="x unified",
        height=620,
        margin={"l": 70, "r": 30, "t": 70, "b": 60},
        legend={"orientation": "h", "yanchor": "bottom", "y": -0.28, "xanchor": "left", "x": 0, "font": {"size": 13}},
        xaxis={"title": xaxis_title, "gridcolor": GRID, "linecolor": BASELINE, "zeroline": False, "ticks": "outside", "tickcolor": BASELINE},
        yaxis={"title": yaxis_title, "gridcolor": GRID, "linecolor": BASELINE, "zeroline": False, "type": yscale or "linear", "rangemode": "tozero"},
    )
    return fig


def add_scheme_traces(fig: go.Figure, frame: pd.DataFrame, x_col: str, y_col: str):
    """One styled trace per scheme: hue=family, dash=Hilbert, marker=data-dep."""
    for scheme in sorted(frame["scheme"].unique()):
        sub = cast(pd.DataFrame, frame[frame["scheme"] == scheme]).sort_values(x_col)
        st = scheme_style(scheme)
        fig.add_trace(
            go.Scatter(
                x=sub[x_col],
                y=sub[y_col],
                name=scheme,
                mode="lines+markers",
                line={"color": st["color"], "dash": st["dash"], "width": 2},
                marker={"symbol": st["symbol"], "size": 8, "color": st["color"], "line": {"color": SURFACE, "width": 1}},
            )
        )


def pow2_ticks(fig: go.Figure, values):
    """Log x-axis with 2^n tick labels (domain sizes are powers of two)."""
    vals = sorted(set(values))
    fig.update_xaxes(type="log", tickvals=vals, ticktext=[f"2<sup>{int(v).bit_length() - 1}</sup>" for v in vals])


# --------------------------------------------------------------------------- #
# Page fragments.
# --------------------------------------------------------------------------- #
def encoding_legend() -> html.Div:
    """The static how-to-read-the-marks card, reused on two pages."""
    family_rows = [
        html.Div(
            [
                html.Span(
                    style={
                        "display": "inline-block",
                        "width": "26px",
                        "height": "3px",
                        "background": FAMILY_COLORS[f],
                        "marginRight": "8px",
                        "verticalAlign": "middle",
                    }
                ),
                html.Span(FAMILY_LABELS[f]),
            ],
            style={"marginBottom": "6px"},
        )
        for f in FAMILY_COLORS
    ]
    return html.Div(
        [
            html.H4("How to read the marks"),
            html.Div(
                [
                    html.Div([html.H5("Hue — scheme family"), *family_rows], className="enc-col"),
                    html.Div(
                        [
                            html.H5("Line — domain"),
                            html.P("── solid: native multi-dimensional"),
                            html.P("╌╌ dashed: Hilbert-linearised"),
                            html.H5("Marker — index divider"),
                            html.P("● circle: uniform splits"),
                            html.P("◆ diamond: data-dependent splits (cells)"),
                            html.P("■ square: data-dependent splits (records)"),
                        ],
                        className="enc-col",
                    ),
                ],
                style={"display": "flex", "gap": "48px", "flexWrap": "wrap"},
            ),
        ],
        className="card",
    )


def overview_page() -> html.Div:
    metric_items = [html.Li([html.Code(m), f" — {doc}"]) for m, doc in METRIC_DOCS.items()]
    return html.Div(
        [
            html.H2("Range Search on Encrypted Multi-Attribute Data — benchmark report"),
            html.P(
                "This site renders the benchmark reports produced by the ers package: "
                "range-search schemes over encrypted multi-attribute data, evaluated on "
                "real and synthetic datasets. Every plotted number comes from an .xlsx "
                "report generated by the benchmark harness — nothing is hand-entered.",
                className="lede",
            ),
            html.Div(
                [
                    html.H4("The pipeline every scheme follows"),
                    html.Ol(
                        [
                            html.Li([html.B("Setup"), " — generate the client's secret keys."]),
                            html.Li(
                                [
                                    html.B("Index construction"),
                                    " — map each data point into the "
                                    "scheme's range-supporting structure and store an encrypted "
                                    "(label → record) entry per covering node.",
                                ]
                            ),
                            html.Li(
                                [html.B("Trapdoor generation"), " — turn a query rectangle into search tokens (one per cover node) that reveal nothing else."]
                            ),
                            html.Li([html.B("Search"), " — the server matches tokens against the encrypted index, never seeing plaintext."]),
                            html.Li([html.B("Resolution"), " — the client decrypts the results and discards false positives."]),
                        ]
                    ),
                    html.P(
                        "Schemes differ in the structure behind step 2 and the cover rule in step 3 — that is exactly what the Scheme guide page documents."
                    ),
                ],
                className="card",
            ),
            html.Div(
                [
                    html.H4("The three trade-off axes"),
                    html.P("Every scheme sits somewhere on a triangle between three costs:"),
                    html.Ul(
                        [
                            html.Li([html.B("Tokens (leakage)"), " — more tokens per query reveal more structure to the server (metric: trapdoor_count)."]),
                            html.Li([html.B("Precision"), " — false positives returned and discarded client-side (metric: precision)."]),
                            html.Li([html.B("Index size"), " — server storage, from replicating each record under every ancestor node (metric: index_size)."]),
                        ]
                    ),
                ],
                className="card",
            ),
            encoding_legend(),
            html.Div(
                [
                    html.H4("Metric reference"),
                    html.Ul(metric_items),
                ],
                className="card",
            ),
            html.Div(
                [
                    html.H4("Reproducing the numbers"),
                    html.P(
                        [
                            "Reports are produced by the CLI, e.g. ",
                            html.Code(
                                "python3 -m ers.benchmark.cli --scheme range_brc --dataset cali --domain-size 6 --records-limit 1000000 --queries-count 250"
                            ),
                            ", or via the per-dataset wrappers in ",
                            html.Code("scripts/"),
                            " (e.g. ",
                            html.Code("scripts/cali.sh range_brc"),
                            "). Point this site at the output folder: ",
                            html.Code("python3 -m ers.benchmark.plot.plot_benchmarks benchmarks"),
                            ".",
                        ]
                    ),
                ],
                className="card",
            ),
        ]
    )


def matrix_cell(text: str, kind: str) -> html.Td:
    return html.Td(text, className=f"mx {kind}")


def schemes_page() -> html.Div:
    """The design-space matrix plus one documentation card per family."""
    header = html.Tr(
        [
            html.Th("Structure + cover"),
            html.Th("Native, uniform"),
            html.Th("Native, data-dep."),
            html.Th("Hilbert, uniform"),
            html.Th("Hilbert, data-dep."),
        ]
    )
    Y, N, X = "yes", "no", "none"  # css classes: implemented / senseless / gap
    rows = [
        ("Linear (no tree)", ("linear", Y), ("—", N), ("linear_hilbert", Y), ("—", N)),
        ("Range + BRC", ("range_brc", Y), ("range_brc_data_dependent", Y), ("range_brc_hilbert", Y), ("range_brc_hilbert_data_dependent", Y)),
        ("TDAG + SRC", ("tdag_src", Y), ("tdag_src_data_dependent", Y), ("tdag_src_hilbert", Y), ("tdag_src_hilbert_data_dependent", Y)),
        ("Quad + BRC", ("quad_brc", Y), ("quad_brc_data_dependent", Y), ("quad_brc_hilbert", Y), ("quad_brc_hilbert_data_dependent", Y)),
        ("Quad + SRC", ("quad_src", Y), ("quad_src_data_dependent", Y), ("quad_src_hilbert", Y), ("quad_src_hilbert_data_dependent", Y)),
        ("Packed R-tree", ("rtree (STR)", Y), ("inherent", N), ("hilbert_rtree", Y), ("inherent", N)),
        ("Interactive (2-round)", ("interactive_src", Y), ("—", X), ("interactive_src_hilbert", Y), ("—", X)),
    ]
    body = [html.Tr([html.Th(r[0])] + [matrix_cell(t, k) for (t, k) in r[1:]]) for r in rows]

    cards = []
    for fd in FAMILY_DOCS:
        chip = html.Span(
            style={
                "display": "inline-block",
                "width": "14px",
                "height": "14px",
                "borderRadius": "3px",
                "background": FAMILY_COLORS[fd["family"]],
                "marginRight": "10px",
                "verticalAlign": "-2px",
            }
        )
        cards.append(
            html.Div(
                [
                    html.H4([chip, FAMILY_LABELS[fd["family"]]]),
                    html.P(fd["what"]),
                    html.P([html.B("Trade-off: "), fd["tradeoff"]]),
                    html.P([html.B("CLI names: ")] + [html.Code(s + ("  " if i < len(fd["schemes"]) - 1 else "")) for i, s in enumerate(fd["schemes"])]),
                ],
                className="card",
            )
        )

    return html.Div(
        [
            html.H2("Scheme guide"),
            html.P(
                "Every implemented scheme is one cell of a four-axis design space: "
                "range-supporting structure × cover strategy × domain representation × "
                "divider. Cells marked — are omitted for a provable reason (see the "
                "family cards); 'inherent' means data-dependence is not a switch for "
                "that structure — bulk-loading is the data-dependence.",
                className="lede",
            ),
            html.Div([html.Table([html.Thead(header), html.Tbody(body)], className="matrix")], className="card", style={"overflowX": "auto"}),
            html.H3("Families"),
            *cards,
            html.H3("Concepts"),
            html.Div(
                [
                    html.H4("BRC vs SRC"),
                    html.P(
                        "A Best Range Cover answers a query with the minimal set of tree nodes "
                        "that exactly tile it: precise, but each node is a separate token. A "
                        "Single Range Cover answers with one node containing the whole query: "
                        "one token, but everything else under that node comes back as false "
                        "positives. TDAGs add overlapping 'cousin' nodes so that the single "
                        "covering node is never much larger than the query."
                    ),
                ],
                className="card",
            ),
            html.Div(
                [
                    html.H4("Hilbert linearisation"),
                    html.P(
                        "A Hilbert curve visits every cell of the d-dimensional grid once, "
                        "preserving locality: nearby cells get nearby curve positions. Mapping "
                        "points to their curve position reduces any dimension to 1-D, where "
                        "simple binary structures work. The cost: a rectangle does not map to "
                        "one curve interval but shatters into disjoint segments — covering "
                        "them singly (SRC) drags in false positives; covering them all (BRC) "
                        "costs tokens. Empirical segment merging trades between the two."
                    ),
                ],
                className="card",
            ),
            html.Div(
                [
                    html.H4("Data-dependent indexing"),
                    html.P(
                        "Uniform dividers cut the domain in half by length; data-dependent "
                        "dividers cut by point mass (the empirical CDF), and the R-trees pack "
                        "the data itself. The index fits skewed data better, but its shape "
                        "becomes client-held state and correlates with the data distribution — "
                        "and the benchmarks show it only pays off when queries follow the same "
                        "distribution as the data."
                    ),
                ],
                className="card",
            ),
        ]
    )


def coverage_page(data: pd.DataFrame) -> html.Div:
    if data.empty:
        return html.Div([html.H2("Coverage"), html.P("No reports loaded.")])
    cov = data.groupby(["scheme", "dataset"])["bits"].agg(lambda s: sorted(set(int(b) for b in s))).reset_index()
    datasets = sorted(data["dataset"].unique())
    schemes = sorted(data["scheme"].unique())
    lookup: dict = {(r["scheme"], r["dataset"]): list(r["bits"]) for _, r in cov.iterrows()}

    header = html.Tr([html.Th("scheme")] + [html.Th(d) for d in datasets])
    body = []
    for s in schemes:
        cells: list = [html.Th(html.Code(s))]
        for d in datasets:
            bits = lookup.get((s, d))
            cells.append(html.Td("·" if not bits else ", ".join(f"2^{b}" for b in bits), className="mx " + ("yes" if bits else "none")))
        body.append(html.Tr(cells))

    return html.Div(
        [
            html.H2("Report coverage"),
            html.P(
                "Domain sizes (bits per dimension) with at least one loaded report, per "
                "scheme and dataset. A dot marks a gap — run the matching scripts/ "
                "wrapper to fill it.",
                className="lede",
            ),
            html.Div([html.Table([html.Thead(header), html.Tbody(body)], className="matrix")], className="card", style={"overflowX": "auto"}),
        ]
    )


def explorer_page(data: pd.DataFrame) -> html.Div:
    if data.empty:
        return html.Div([html.H2("Explorer"), html.P("No reports loaded — generate some with the scripts/ wrappers and restart.")])
    schemes = sorted(data["scheme"].unique())
    datasets = sorted(data["dataset"].unique())
    metrics = sorted(data["metric"].unique())
    return html.Div(
        [
            html.H2("Explorer"),
            html.P(
                "Pick schemes, a dataset and a metric; then the axis. Hue = family, "
                "dashed = Hilbert, diamond = data-dependent (full legend on the "
                "Overview page).",
                className="lede",
            ),
            html.Div(
                [
                    # maxHeight controls how tall the *open* option menu is —
                    # the default 200px shows barely five of the 20+ schemes.
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Label("Schemes"),
                                    html.Span(
                                        [
                                            html.Button("Select all", id="schemes-all", n_clicks=0, className="mini-btn"),
                                            html.Button("Clear all", id="schemes-none", n_clicks=0, className="mini-btn"),
                                        ],
                                        className="btn-row",
                                    ),
                                ],
                                className="label-row",
                            ),
                            dcc.Dropdown(id="scheme-filter", options=[{"label": s, "value": s} for s in schemes], value=[], multi=True, maxHeight=480),
                        ],
                        className="ctl ctl-wide",
                    ),
                    html.Div(
                        [
                            html.Label("Dataset"),
                            dcc.Dropdown(id="dataset-filter", options=[{"label": d, "value": d} for d in datasets], value=datasets[0], maxHeight=480),
                        ],
                        className="ctl",
                    ),
                    html.Div(
                        [
                            html.Label("Metric"),
                            dcc.Dropdown(
                                id="metric-filter",
                                options=[{"label": m, "value": m} for m in metrics],
                                value="trapdoor_count" if "trapdoor_count" in metrics else metrics[0],
                                maxHeight=480,
                            ),
                        ],
                        className="ctl",
                    ),
                    html.Div(
                        [
                            html.Label("X-axis"),
                            dcc.Dropdown(
                                id="xaxis-selector",
                                options=[{"label": "Query size (% of domain)", "value": "query_size"}, {"label": "Domain size", "value": "domain_size"}],
                                value="domain_size",
                                maxHeight=480,
                            ),
                        ],
                        className="ctl",
                    ),
                    # The slice pins the variable NOT on the x-axis: plotting
                    # against query size requires fixing one domain size, and
                    # vice versa. The label spells that out per selection.
                    html.Div(
                        [html.Label("Slice", id="secondary-label"), dcc.Dropdown(id="secondary-filter", value="average", maxHeight=480)],
                        className="ctl",
                    ),
                    html.Div(
                        [
                            html.Label("Y scale"),
                            dcc.Dropdown(
                                id="yaxis-scale",
                                options=[{"label": "Linear", "value": "linear"}, {"label": "Logarithmic", "value": "log"}],
                                value="linear",
                                clearable=False,
                                maxHeight=480,
                            ),
                        ],
                        className="ctl",
                    ),
                ],
                className="controls",
            ),
            dcc.Graph(id="performance-plot", config={"displaylogo": False}),
            html.P(id="metric-caption", className="caption"),
        ]
    )


# --------------------------------------------------------------------------- #
# App assembly.
# --------------------------------------------------------------------------- #
INDEX_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
  {%metas%}<title>ERS benchmark report</title>{%favicon%}{%css%}
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; background: __PAGE_BG__; color: __INK__;
           font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
    .shell { display: flex; min-height: 100vh; }
    .sidebar { width: 230px; flex-shrink: 0; background: __SURFACE__;
               border-right: 1px solid __BORDER__; padding: 28px 20px; }
    .sidebar h1 { font-size: 16px; line-height: 1.35; margin: 0 0 4px; }
    .sidebar .sub { font-size: 12.5px; color: __INK_MUTED__; margin-bottom: 24px; }
    .sidebar a { display: block; padding: 9px 12px; margin: 2px 0; border-radius: 7px;
                 color: __INK_SECONDARY__; text-decoration: none; font-size: 14.5px; }
    .sidebar a:hover { background: __PAGE_BG__; }
    .sidebar a.active { background: __PAGE_BG__; color: __INK__; font-weight: 600; }
    .content { flex: 1; padding: 34px 44px; max-width: 1200px; }
    h2 { margin-top: 0; font-size: 26px; }
    h3 { margin-top: 34px; }
    .lede { color: __INK_SECONDARY__; font-size: 15.5px; max-width: 72ch; line-height: 1.55; }
    .card { background: __SURFACE__; border: 1px solid __BORDER__; border-radius: 10px;
            padding: 18px 22px; margin: 16px 0; }
    .card h4 { margin: 2px 0 10px; } .card h5 { margin: 12px 0 6px; color: __INK_SECONDARY__; }
    .card p, .card li { line-height: 1.55; font-size: 14.5px; color: __INK_SECONDARY__; }
    .card p { margin: 6px 0; }
    code { background: __PAGE_BG__; border: 1px solid __BORDER__; border-radius: 4px;
           padding: 1px 5px; font-size: 13px; }
    .controls { display: flex; flex-wrap: wrap; gap: 14px; margin: 18px 0;
                background: __SURFACE__; border: 1px solid __BORDER__;
                border-radius: 10px; padding: 14px 16px; }
    .ctl { flex: 1 1 170px; min-width: 170px; }
    .ctl-wide { flex: 3 1 340px; }
    .ctl label { display: block; font-size: 12.5px; color: __INK_MUTED__;
                 margin-bottom: 4px; font-weight: 600; }
    .label-row { display: flex; align-items: center; justify-content: space-between;
                 gap: 10px; margin-bottom: 4px; }
    .label-row label { margin-bottom: 0; }
    .btn-row { display: inline-flex; gap: 6px; }
    .mini-btn { font: inherit; font-size: 12px; line-height: 1; cursor: pointer;
                padding: 4px 9px; border: 1px solid __BORDER__; border-radius: 6px;
                background: __PAGE_BG__; color: __INK_SECONDARY__; }
    .mini-btn:hover { background: __SURFACE__; color: __INK__; border-color: __INK_MUTED__; }
    .caption { color: __INK_MUTED__; font-size: 13.5px; max-width: 80ch; }
    table.matrix { border-collapse: collapse; font-size: 13.5px; width: 100%; }
    table.matrix th, table.matrix td { border: 1px solid __GRID__; padding: 7px 10px;
                                       text-align: left; }
    table.matrix thead th { background: __PAGE_BG__; }
    td.mx.yes { } td.mx.no { color: __INK_MUTED__; }
    td.mx.none { color: __INK_MUTED__; font-style: italic; }
    .enc-col p { margin: 4px 0; color: __INK_SECONDARY__; font-size: 14px; }
  </style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>"""
for token, value in [
    ("__PAGE_BG__", PAGE_BG),
    ("__SURFACE__", SURFACE),
    ("__INK__", INK),
    ("__INK_SECONDARY__", INK_SECONDARY),
    ("__INK_MUTED__", INK_MUTED),
    ("__BORDER__", BORDER),
    ("__GRID__", GRID),
]:
    INDEX_TEMPLATE = INDEX_TEMPLATE.replace(token, value)


def build_app(data: pd.DataFrame) -> dash.Dash:
    """Assemble the multi-page app over the loaded report frame."""
    app = dash.Dash(__name__, suppress_callback_exceptions=True)
    app.index_string = INDEX_TEMPLATE

    nav = [("Overview", "/"), ("Scheme guide", "/schemes"), ("Explorer", "/explorer"), ("Coverage", "/coverage")]
    app.layout = html.Div(
        [
            dcc.Location(id="url"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("ERS benchmarks"),
                            html.Div("Range search on encrypted multi-attribute data", className="sub"),
                            html.Div([dcc.Link(label, href=href, id=f"nav-{href.strip('/') or 'home'}", className="navlink") for label, href in nav], id="nav"),
                        ],
                        className="sidebar",
                    ),
                    html.Div(id="page", className="content"),
                ],
                className="shell",
            ),
        ]
    )

    @app.callback(Output("page", "children"), Input("url", "pathname"))
    def route(pathname):
        if pathname == "/schemes":
            return schemes_page()
        if pathname == "/explorer":
            return explorer_page(data)
        if pathname == "/coverage":
            return coverage_page(data)
        return overview_page()

    all_schemes = sorted(data["scheme"].unique()) if not data.empty else []

    @app.callback(
        Output("scheme-filter", "value"),
        Input("schemes-all", "n_clicks"),
        Input("schemes-none", "n_clicks"),
        prevent_initial_call=True,
    )
    def bulk_select(_all_clicks, _none_clicks):
        """Select-all / clear-all shortcuts for the scheme picker."""
        return all_schemes if ctx.triggered_id == "schemes-all" else []

    @app.callback(
        Output("secondary-filter", "options"),
        Output("secondary-filter", "value"),
        Output("secondary-label", "children"),
        Input("xaxis-selector", "value"),
        Input("dataset-filter", "value"),
    )
    def update_secondary_options(xaxis, dataset):
        """
        The slice control pins the variable that is NOT on the x-axis:
        an x-axis over query sizes needs one fixed domain size, and an x-axis
        over domain sizes needs one fixed query size (or the average).
        """
        if not dataset:
            return [], None, "Slice"
        filtered = cast(pd.DataFrame, data[data["dataset"] == dataset])
        if xaxis == "query_size":
            rows = cast(pd.DataFrame, filtered[["domain_size", "dim", "bits"]]).drop_duplicates().sort_values("domain_size")
            opts = [
                {"label": f"domain 2^{int(rr['dim'] * rr['bits'])} ({int(rr['dim'])}D, {int(rr['bits'])} bits/dim)", "value": int(rr["domain_size"])}
                for rr in (cast(Any, r) for _, r in rows.iterrows())
            ]
            return opts, (opts[0]["value"] if opts else None), "At domain size"
        q_sizes = sorted(cast(pd.Series, filtered["query_size"]).dropna().unique())
        opts = [{"label": "Average over query sizes", "value": "average"}] + [{"label": f"query size {q}%", "value": q} for q in q_sizes]
        return opts, "average", "At query size"

    @app.callback(
        Output("performance-plot", "figure"),
        Output("metric-caption", "children"),
        Input("scheme-filter", "value"),
        Input("dataset-filter", "value"),
        Input("metric-filter", "value"),
        Input("xaxis-selector", "value"),
        Input("yaxis-scale", "value"),
        Input("secondary-filter", "value"),
    )
    def update_plot(schemes, dataset, metric, xaxis, yscale, secondary):
        caption = METRIC_DOCS.get(metric, "")
        if not schemes or not dataset or not metric:
            fig = base_figure("Select schemes, a dataset and a metric", "", "", "linear")
            return fig, caption

        frame = cast(pd.DataFrame, data[data["scheme"].isin(schemes) & (data["dataset"] == dataset) & (data["metric"] == metric)])
        if frame.empty:
            fig = base_figure("No reports match this selection — see the Coverage page", "", "", "linear")
            return fig, caption

        pretty = metric.replace("_", " ")

        if metric in QUERYLESS_METRICS:
            frame = frame.sort_values("domain_size")
            fig = base_figure(f"{pretty} — {dataset}", "domain size (points)", pretty, yscale)
            add_scheme_traces(fig, frame, "domain_size", metric)
            pow2_ticks(fig, frame["domain_size"])
            return fig, caption

        if xaxis == "query_size":
            frame = cast(pd.DataFrame, frame[frame["domain_size"] == secondary])
            fig = base_figure(f"{pretty} vs query size — {dataset}", "query size (% of domain per dimension)", pretty, yscale)
            add_scheme_traces(fig, frame, "query_size", metric)
            return fig, caption

        if secondary == "average":
            frame = cast(pd.DataFrame, frame.groupby(["scheme", "domain_size"], as_index=False)[metric].mean())
            subtitle = "averaged over query sizes"
        else:
            frame = cast(pd.DataFrame, frame[frame["query_size"] == secondary])
            subtitle = f"query size {secondary}"
        frame = frame.sort_values("domain_size")
        fig = base_figure(f"{pretty} vs domain size — {dataset} ({subtitle})", "domain size (points)", pretty, yscale)
        add_scheme_traces(fig, frame, "domain_size", metric)
        pow2_ticks(fig, frame["domain_size"])
        return fig, caption

    return app


def main():
    parser = argparse.ArgumentParser(description="Serve the benchmark report site.")
    parser.add_argument("folder", nargs="?", default="benchmarks", help="folder containing the .xlsx reports (default: benchmarks)")
    parser.add_argument("--port", type=int, default=8050)
    parser.add_argument("--debug", action="store_true", help="enable the Dash dev-tools / hot reload")
    args = parser.parse_args()

    data = load_all_data(args.folder)
    if data.empty:
        print(f"Warning: no reports found under '{args.folder}'.", file=sys.stderr)
    app = build_app(data)
    app.run(debug=args.debug, port=args.port)


if __name__ == "__main__":
    main()
