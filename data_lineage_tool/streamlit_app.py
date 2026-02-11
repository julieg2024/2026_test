"""Streamlit web dashboard for interactive data lineage exploration."""

import json
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

# Color scheme for node types
COLOR_MAP = {
    "table": "#4A90D9",
    "view": "#7B68EE",
    "column": "#50C878",
    "cte": "#FFB347",
}

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
    """Render the lineage graph using streamlit-agraph."""
    if focus_node and focus_node in G:
        G = get_subgraph_for_node(G, focus_node)

    nodes = []
    edges = []

    for node_id in G.nodes:
        node_data = G.nodes[node_id]
        node_type = node_data.get("node_type", "table")
        nodes.append(Node(
            id=node_id,
            label=node_id,
            color=COLOR_MAP.get(node_type, "#999999"),
            shape=SHAPE_MAP.get(node_type, "box"),
            size=30 if node_data.get("level") == "table" else 18,
            title=f"Type: {node_type}\nFile: {node_data.get('source_file', 'N/A')}",
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
        physics=True,
        hierarchical=True,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
    )

    return agraph(nodes=nodes, edges=edges, config=config)


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

    # Tables list
    with st.expander("All Tables", expanded=False):
        for name in sorted(lineage.tables):
            t = lineage.tables[name]
            src = f" ({t.source_file})" if t.source_file else ""
            st.write(f"- **{t.node_type.value}** `{name}`{src}")

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
