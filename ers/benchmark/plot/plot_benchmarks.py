import dash
from dash import dcc, html, Input, Output
import pandas as pd
import plotly.express as px
import os
import sys

app = dash.Dash(__name__, suppress_callback_exceptions=False)

QUERYLESS_METRICS = {"index_size", "index_time"}

# --- Load Data ---
def split_scheme_and_dataset(parts):
    for i in range(len(parts)):
        if i < len(parts) - 1 and parts[i] == "dense" and parts[i + 1] == "2d":
            scheme = "_".join(parts[:i])
            dataset = "dense_2d"
            return scheme, dataset, parts[i + 2:]
        if parts[i] == "cali" or parts[i] == "spitz" or parts[i] == "gowalla" or parts[i] == "nh":
            scheme = "_".join(parts[:i])
            dataset = parts[i]
            return scheme, dataset, parts[i + 1:]
    raise ValueError(f"Dataset not found in parts: {parts}")

def load_all_data(root_folder):
    entries = []
    for dirpath, _, filenames in os.walk(root_folder):
        for file in filenames:
            if not file.endswith(".xlsx"):
                continue
            path = os.path.join(dirpath, file)
            name = file[:-5]
            parts = name.split("_")

            try:
                scheme, dataset, tail = split_scheme_and_dataset(parts)
                dim, bits = int(tail[0]), int(tail[1])
                max_q, num_q = int(tail[2]), int(tail[3])
                domain_size = 2 ** (dim * bits)

                sheets = pd.read_excel(path, header=None, sheet_name=None, engine="openpyxl")
                for metric, df in sheets.items():
                    if df.empty:
                        continue
                    if df.shape[1] >= 2:
                        df = df.iloc[:, :2]
                        df.columns = ["query_size", metric]
                        df = df.dropna()
                    elif df.shape[0] == 1 and df.shape[1] == 1:
                        val = df.iloc[0, 0]
                        df = pd.DataFrame({"query_size": [None], metric: [val]})
                    else:
                        continue

                    df["scheme"] = scheme
                    df["dataset"] = dataset
                    df["dim"] = dim
                    df["bits"] = bits
                    df["domain_size"] = domain_size
                    df["num_queries"] = num_q
                    df["max_query_size"] = max_q
                    df["metric"] = metric
                    entries.append(df)
            except Exception as e:
                print(f"Skipping {file}: {e}")

    return pd.concat(entries, ignore_index=True) if entries else pd.DataFrame()

source_dir = sys.argv[1] if len(sys.argv) > 1 else "."
data = load_all_data(source_dir)

# --- Layout ---
app.layout = html.Div([
    html.H2("Scheme Performance Visualization"),

    html.Div([
        html.Label("Select Schemes:"),
        dcc.Dropdown(
            id="scheme-filter",
            options=[{"label": s, "value": s} for s in sorted(data["scheme"].unique())],
            value=sorted(data["scheme"].unique()),
            multi=True,
            style={"width": "100%"}
        )
    ], style={"padding": "10px 0"}),

    html.Div([
        html.Label("Select Dataset:"),
        dcc.Dropdown(
            id="dataset-filter",
            options=[{"label": d, "value": d} for d in sorted(data["dataset"].unique())],
            value=None,
            style={"width": "100%"}
        )
    ], style={"padding": "10px 0"}),

    html.Div([
        html.Label("Select Metric:"),
        dcc.Dropdown(
            id="metric-filter",
            options=[{"label": m, "value": m} for m in sorted(data["metric"].unique())],
            value=None,
            style={"width": "100%"}
        )
    ], style={"padding": "10px 0"}),

    html.Div(id="xaxis-container", children=[
        html.Label("Select X-axis:"),
        dcc.Dropdown(
            id="xaxis-selector",
            options=[
                {"label": "Query Size (%)", "value": "query_size"},
                {"label": "Domain Size", "value": "domain_size"},
            ],
            value=None,
            style={"width": "100%"}
        )
    ], style={"padding": "10px 0", "display": "none"}),

    html.Div(id="secondary-container", children=[
        html.Label("Select Filter:"),
        dcc.Dropdown(id="secondary-filter", value=None, style={"width": "100%"})
    ], style={"padding": "10px 0", "display": "none"}),

    html.Div(id="yaxis-container", children=[
        html.Label("Y-axis Scale:"),
        dcc.Dropdown(
            id="yaxis-scale",
            options=[
                {"label": "Linear", "value": "linear"},
                {"label": "Logarithmic", "value": "log"},
            ],
            value=None,
            style={"width": "100%"}
        )
    ], style={"padding": "10px 0", "display": "none"}),

    dcc.Graph(id="performance-plot")
])

# --- Toggle visibility of UI elements ---
@app.callback(
    Output("xaxis-container", "style"),
    Output("secondary-container", "style"),
    Output("yaxis-container", "style"),
    Input("metric-filter", "value")
)
def toggle_input_visibility(metric):
    if not metric:
        return {"display": "none"}, {"display": "none"}, {"display": "none"}
    if metric in QUERYLESS_METRICS:
        return {"display": "none"}, {"display": "none"}, {"display": "block"}
    return {"display": "block"}, {"display": "block"}, {"display": "block"}

# --- Update secondary filter options ---
@app.callback(
    Output("secondary-filter", "options"),
    Input("xaxis-selector", "value"),
    Input("dataset-filter", "value"),
    Input("metric-filter", "value")
)
def update_secondary_options(xaxis, dataset, metric):
    if not dataset or not metric or not xaxis:
        return []
    filtered = data[data["dataset"] == dataset]
    if xaxis == "query_size":
        domain_rows = filtered[["domain_size", "dim", "bits"]].drop_duplicates()
        domain_rows["label"] = domain_rows.apply(
            lambda r: f"2^{r['dim'] * r['bits']} (dim={r['dim']}, bits={r['bits']})", axis=1
        )
        return [{"label": r["label"], "value": r["domain_size"]} for _, r in domain_rows.iterrows()]
    elif xaxis == "domain_size":
        q_sizes = sorted(filtered["query_size"].dropna().unique())
        return [{"label": str(q), "value": q} for q in q_sizes] + [{"label": "Average", "value": "average"}]
    return []

# --- Plotting logic ---
@app.callback(
    Output("performance-plot", "figure"),
    Input("scheme-filter", "value"),
    Input("dataset-filter", "value"),
    Input("metric-filter", "value"),
    Input("xaxis-selector", "value"),
    Input("yaxis-scale", "value"),
    Input("secondary-filter", "value")
)
def update_plot(schemes, dataset, metric, xaxis, yscale, secondary):
    if not all([schemes, dataset, metric]):
        return px.line(title="Waiting for input...")

    filtered = data[
        data["scheme"].isin(schemes) &
        (data["dataset"] == dataset) &
        (data["metric"] == metric)
    ]

    def format_ticks(values):
        values = sorted(set(values))
        return values, [f"2^{int(v).bit_length()-1}" for v in values]

    if metric in QUERYLESS_METRICS:
        filtered = filtered.sort_values("domain_size")
        fig = px.line(
            filtered, x="domain_size", y=metric, color="scheme", markers=True,
            title=f"{metric.replace('_',' ').title()} vs Domain Size"
        )
        vals, labels = format_ticks(filtered["domain_size"])
        fig.update_xaxes(type="log", tickvals=vals, ticktext=labels)
        fig.update_layout(yaxis_type=yscale or "linear")
        return fig

    if not all([xaxis, secondary]):
        return px.line(title="Waiting for full selection...")

    if xaxis == "query_size":
        filtered = filtered[filtered["domain_size"] == secondary]
        filtered = filtered.sort_values("query_size")
        fig = px.line(
            filtered, x="query_size", y=metric, color="scheme", markers=True,
            title=f"{metric.replace('_',' ').title()} vs Query Size"
        )
        fig.update_layout(yaxis_type=yscale or "linear")
        return fig

    if xaxis == "domain_size":
        if secondary == "average":
            filtered = filtered.groupby(["scheme", "domain_size"], as_index=False)[metric].mean()
        else:
            filtered = filtered[filtered["query_size"] == int(secondary)]
        filtered = filtered.sort_values("domain_size")
        fig = px.line(
            filtered, x="domain_size", y=metric, color="scheme", markers=True,
            title=f"{metric.replace('_',' ').title()} vs Domain Size"
        )
        vals, labels = format_ticks(filtered["domain_size"])
        fig.update_xaxes(type="log", tickvals=vals, ticktext=labels)
        fig.update_layout(yaxis_type=yscale or "linear")
        return fig

    return px.line(title="Invalid selection.")

if __name__ == "__main__":
    app.run_server(debug=True)
