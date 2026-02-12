"""Streamlit web dashboard for interactive data lineage exploration."""

import json
from collections import defaultdict
from pathlib import Path

import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config

from data_lineage_tool.github_connector import resolve_source
from data_lineage_tool.sql_scanner import scan_directory
from data_lineage_tool.sql_parser import parse_sql_files
from data_lineage_tool.graph_builder import (
    build_graph,
    get_subgraph_for_node,
    get_upstream,
    get_downstream,
    to_dict,
)
from data_lineage_tool.visualizer import LAYER_ORDER, LAYER_STYLES


st.set_page_config(page_title="Data Lineage Explorer", layout="wide")
st.title("Data Lineage Explorer")

# --- Sidebar controls ---
with st.sidebar:
    st.header("Configuration")

    source = st.text_input(
        "SQL Source",
        placeholder="GitHub URL or local path",
        help="Enter a GitHub repo URL or a local directory path containing SQL files",
    )
    branch = st.text_input("Branch (optional)", placeholder="main")
    dialect = st.selectbox(
        "SQL Dialect",
        [None, "bigquery", "snowflake", "postgres", "mysql", "duckdb", "spark", "trino", "redshift"],
        format_func=lambda x: "Auto-detect" if x is None else x,
    )
    level = st.radio("Lineage Level", ["table", "column", "all"], index=0)

    analyze_btn = st.button("Analyze", type="primary", use_container_width=True)

    # Layer legend
    st.markdown("---")
    st.subheader("Layer Legend")
    for layer_key in LAYER_ORDER:
        style = LAYER_STYLES[layer_key]
        st.markdown(
            f'<span style="display:inline-block;width:14px;height:14px;'
            f'background:{style["node_fill"]};border-radius:3px;margin-right:6px;'
            f'vertical-align:middle;"></span> {style["label"]}',
            unsafe_allow_html=True,
        )

# Layer-based color mapping for agraph nodes
LAYER_COLOR_MAP = {l: s["node_fill"] for l, s in LAYER_STYLES.items()}

SHAPE_MAP = {
    "table": "box",
    "view": "diamond",
    "column": "dot",
    "cte": "triangle",
}


def run_analysis(source_path: str, branch_name: str | None, sql_dialect: str | None, lineage_level: str):
    """Run the full lineage analysis pipeline."""
    repo_path = resolve_source(source_path, branch=branch_name or None)
    sql_files = scan_directory(repo_path)

    if not sql_files:
        st.warning("No SQL files found in the specified source.")
        return None, None, []

    lineage = parse_sql_files(sql_files, dialect=sql_dialect)
    graph = build_graph(lineage, level=lineage_level)
    return graph, lineage, sql_files


def render_graph(G, focus_node=None):
    """Render the lineage graph using streamlit-agraph with layer-based hierarchy."""
    if focus_node and focus_node in G:
        G = get_subgraph_for_node(G, focus_node)

    nodes = []
    edges = []

    # Assign hierarchical level values to enforce left-to-right layer ordering.
    # vis.js hierarchical layout uses the 'level' property to position nodes.
    layer_level_map = {l: i for i, l in enumerate(LAYER_ORDER)}

    for node_id in G.nodes:
        node_data = G.nodes[node_id]
        node_type = node_data.get("node_type", "table")
        layer = node_data.get("layer", "unknown")
        color = LAYER_COLOR_MAP.get(layer, "#95A5A6")
        hier_level = layer_level_map.get(layer, len(LAYER_ORDER))

        nodes.append(Node(
            id=node_id,
            label=node_id,
            color=color,
            shape=SHAPE_MAP.get(node_type, "box"),
            size=30 if node_data.get("level") == "table" else 18,
            level=hier_level,
            title=f"Layer: {layer}\nType: {node_type}\nFile: {node_data.get('source_file', 'N/A')}",
        ))

    for u, v in G.edges:
        edge_data = G.edges[u, v]
        transform = edge_data.get("transformation", "")
        edges.append(Edge(
            source=u,
            target=v,
            label=transform if transform else "",
            color="#888888",
        ))

    config = Config(
        width=900,
        height=600,
        directed=True,
        physics=False,
        hierarchical=True,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
    )

    return agraph(nodes=nodes, edges=edges, config=config)


def _render_layer_section(graph, layer_key, lineage):
    """Render a collapsible section showing tables for a single layer."""
    style = LAYER_STYLES[layer_key]
    layer_tables = [
        n for n in graph.nodes
        if graph.nodes[n].get("layer") == layer_key
    ]
    if not layer_tables:
        return

    st.markdown(
        f'<div style="background:{style["bg"]};border-left:4px solid {style["border"]};'
        f'padding:8px 12px;margin-bottom:8px;border-radius:4px;">'
        f'<strong>{style["label"]}</strong> &mdash; {len(layer_tables)} table(s)</div>',
        unsafe_allow_html=True,
    )
    for name in sorted(layer_tables):
        t = lineage.tables.get(name)
        if t:
            src = f" ({t.source_file})" if t.source_file else ""
            st.write(f"  - **{t.node_type.value}** `{name}`{src}")


# --- Main content ---
if analyze_btn and source:
    with st.spinner("Analyzing SQL files..."):
        try:
            graph, lineage, sql_files = run_analysis(source, branch, dialect, level)
        except FileNotFoundError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

    if graph is None:
        st.stop()

    # Store in session state
    st.session_state["graph"] = graph
    st.session_state["lineage"] = lineage
    st.session_state["sql_files"] = sql_files

if "graph" in st.session_state:
    graph = st.session_state["graph"]
    lineage = st.session_state["lineage"]
    sql_files = st.session_state["sql_files"]

    # Stats bar
    col1, col2, col3 = st.columns(3)
    col1.metric("SQL Files", len(sql_files))
    col2.metric("Tables/Views", len(lineage.tables))
    col3.metric("Lineage Edges", len(lineage.edges))

    # Layer distribution
    layer_counts: dict[str, int] = defaultdict(int)
    for n in graph.nodes:
        layer_counts[graph.nodes[n].get("layer", "unknown")] += 1

    layer_cols = st.columns(len(LAYER_ORDER))
    for col, layer_key in zip(layer_cols, LAYER_ORDER):
        count = layer_counts.get(layer_key, 0)
        if count:
            style = LAYER_STYLES[layer_key]
            col.markdown(
                f'<div style="text-align:center;background:{style["bg"]};'
                f'border:2px solid {style["border"]};border-radius:8px;padding:8px;">'
                f'<div style="font-size:22px;font-weight:bold;color:{style["border"]}">{count}</div>'
                f'<div style="font-size:12px;color:#555">{style["label"]}</div></div>',
                unsafe_allow_html=True,
            )

    # Focus selector
    table_names = sorted(graph.nodes)
    focus_options = ["(All tables)"] + table_names
    focus = st.selectbox("Focus on table", focus_options)
    focus_node = None if focus == "(All tables)" else focus

    # Graph visualization
    st.subheader("Lineage Graph")
    render_graph(graph, focus_node=focus_node)

    # Node details
    if focus_node and focus_node in graph:
        st.subheader(f"Details: {focus_node}")

        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            upstream = get_upstream(graph, focus_node)
            st.write(f"**Upstream ({len(upstream)}):**")
            for u in sorted(upstream):
                st.write(f"- {u}")

        with detail_col2:
            downstream = get_downstream(graph, focus_node)
            st.write(f"**Downstream ({len(downstream)}):**")
            for d in sorted(downstream):
                st.write(f"- {d}")

        node_data = graph.nodes[focus_node]
        if node_data.get("source_file"):
            st.write(f"**Defined in:** `{node_data['source_file']}`")

    # Tables grouped by layer
    with st.expander("All Tables (by Layer)", expanded=False):
        for layer_key in LAYER_ORDER:
            _render_layer_section(graph, layer_key, lineage)

    # JSON export
    with st.expander("Export JSON", expanded=False):
        graph_data = to_dict(graph)
        st.json(graph_data)
        st.download_button(
            "Download JSON",
            data=json.dumps(graph_data, indent=2),
            file_name="lineage.json",
            mime="application/json",
        )

elif not analyze_btn:
    st.info("Enter a GitHub URL or local path in the sidebar and click **Analyze** to get started.")
