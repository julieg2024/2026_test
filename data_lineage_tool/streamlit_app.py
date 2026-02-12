"""Streamlit web dashboard for interactive data lineage exploration."""

import json
from collections import defaultdict
from pathlib import Path

import graphviz as gv
import streamlit as st

from data_lineage_tool.github_connector import resolve_source
from data_lineage_tool.sql_scanner import scan_directory
from data_lineage_tool.sql_parser import parse_sql_files
from data_lineage_tool.graph_builder import (
    build_graph,
    find_all_paths,
    find_path,
    get_downstream,
    get_impact,
    get_leaf_nodes,
    get_root_nodes,
    get_subgraph_for_node,
    get_upstream,
    search_nodes,
    to_dict,
)
from data_lineage_tool.visualizer import LAYER_ORDER, LAYER_STYLES, to_graphviz


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


def _render_dot_as_image(dot_source: str):
    """Render DOT source as a PNG image via server-side Graphviz.

    Uses st.image with PNG bytes so the proper Graphviz layout engine
    handles clusters and hierarchy (the JS-based st.graphviz_chart
    does not support subgraph clusters reliably).
    """
    src = gv.Source(dot_source)
    png_bytes = src.pipe(format="png")
    st.image(png_bytes, use_container_width=True)


def render_graph(G, focus_node=None):
    """Render the lineage graph with layer-based hierarchy."""
    if focus_node and focus_node in G:
        G = get_subgraph_for_node(G, focus_node)

    dot_source = to_graphviz(G)
    _render_dot_as_image(dot_source)


def render_path_graph(G, path_nodes):
    """Render a subgraph highlighting a specific path."""
    subgraph = G.subgraph(path_nodes).copy()
    dot_source = to_graphviz(subgraph)
    _render_dot_as_image(dot_source)


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
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("SQL Files", len(sql_files))
    col2.metric("Tables/Views", len(lineage.tables))
    col3.metric("Lineage Edges", len(lineage.edges))
    col4.metric("Root Tables", len(get_root_nodes(graph)))
    col5.metric("Leaf Tables", len(get_leaf_nodes(graph)))

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

    # Tabs for different exploration modes
    tab_graph, tab_impact, tab_trace, tab_search, tab_tables, tab_export = st.tabs(
        ["Lineage Graph", "Impact Analysis", "Path Tracer", "Search", "All Tables", "Export"]
    )

    # --- Tab: Lineage Graph ---
    with tab_graph:
        table_names = sorted(graph.nodes)
        focus_options = ["(All tables)"] + table_names
        focus = st.selectbox("Focus on table", focus_options, key="graph_focus")
        focus_node = None if focus == "(All tables)" else focus

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

    # --- Tab: Impact Analysis ---
    with tab_impact:
        st.subheader("Impact Analysis")
        st.caption("Select a table to see what would be affected if it changes.")

        impact_table = st.selectbox(
            "Select table to analyze",
            sorted(graph.nodes),
            key="impact_table",
        )

        if impact_table:
            result = get_impact(graph, impact_table)

            if result["total"] == 0:
                st.info(f"**{impact_table}** has no downstream dependents (it's a leaf node).")
            else:
                st.warning(
                    f"Changing **{impact_table}** would affect "
                    f"**{result['total']}** downstream table(s)."
                )

                impact_col1, impact_col2 = st.columns(2)
                with impact_col1:
                    st.write(f"**Direct dependents ({len(result['direct'])}):**")
                    for n in sorted(result["direct"]):
                        layer = graph.nodes[n].get("layer", "unknown")
                        style = LAYER_STYLES.get(layer, LAYER_STYLES["unknown"])
                        st.markdown(
                            f'<span style="display:inline-block;width:10px;height:10px;'
                            f'background:{style["node_fill"]};border-radius:2px;'
                            f'margin-right:4px;vertical-align:middle;"></span> {n}',
                            unsafe_allow_html=True,
                        )

                with impact_col2:
                    st.write(f"**Indirect dependents ({len(result['indirect'])}):**")
                    for n in sorted(result["indirect"]):
                        layer = graph.nodes[n].get("layer", "unknown")
                        style = LAYER_STYLES.get(layer, LAYER_STYLES["unknown"])
                        st.markdown(
                            f'<span style="display:inline-block;width:10px;height:10px;'
                            f'background:{style["node_fill"]};border-radius:2px;'
                            f'margin-right:4px;vertical-align:middle;"></span> {n}',
                            unsafe_allow_html=True,
                        )

                if result["by_layer"]:
                    st.write("**Affected by layer:**")
                    for layer_key in LAYER_ORDER:
                        nodes = result["by_layer"].get(layer_key, [])
                        if nodes:
                            style = LAYER_STYLES[layer_key]
                            st.markdown(
                                f'<div style="background:{style["bg"]};border-left:4px solid {style["border"]};'
                                f'padding:6px 10px;margin-bottom:4px;border-radius:4px;">'
                                f'<strong>{style["label"]}:</strong> {", ".join(nodes)}</div>',
                                unsafe_allow_html=True,
                            )

                # Show impact subgraph
                st.write("**Impact graph:**")
                impact_nodes = result["direct"] | result["indirect"] | {impact_table}
                render_path_graph(graph, impact_nodes)

    # --- Tab: Path Tracer ---
    with tab_trace:
        st.subheader("Path Tracer")
        st.caption("Trace the data flow path between any two tables.")

        trace_col1, trace_col2 = st.columns(2)
        with trace_col1:
            from_table = st.selectbox("From table", sorted(graph.nodes), key="trace_from")
        with trace_col2:
            to_table = st.selectbox("To table", sorted(graph.nodes), key="trace_to")

        show_all = st.checkbox("Show all paths (not just shortest)")

        if from_table and to_table and from_table != to_table:
            if show_all:
                paths = find_all_paths(graph, from_table, to_table)
                if not paths:
                    st.info(f"No path exists from **{from_table}** to **{to_table}**.")
                else:
                    st.success(f"Found **{len(paths)}** path(s) from **{from_table}** to **{to_table}**.")
                    for i, p in enumerate(paths, 1):
                        st.write(f"**Path {i}:** {' -> '.join(p)}")
                    # Visualize all nodes involved
                    all_nodes = set()
                    for p in paths:
                        all_nodes.update(p)
                    render_path_graph(graph, all_nodes)
            else:
                path = find_path(graph, from_table, to_table)
                if not path:
                    st.info(f"No path exists from **{from_table}** to **{to_table}**.")
                else:
                    st.success(f"**Shortest path:** {' -> '.join(path)}")
                    render_path_graph(graph, set(path))
        elif from_table == to_table:
            st.info("Select two different tables to trace a path.")

    # --- Tab: Search ---
    with tab_search:
        st.subheader("Search Tables")
        query = st.text_input("Search by name", placeholder="e.g. customer, order, mart")

        if query:
            results = search_nodes(graph, query)
            if results:
                st.write(f"Found **{len(results)}** matching table(s):")
                for name in results:
                    node_data = graph.nodes[name]
                    layer = node_data.get("layer", "unknown")
                    style = LAYER_STYLES.get(layer, LAYER_STYLES["unknown"])
                    node_type = node_data.get("node_type", "table")
                    source_file = node_data.get("source_file", "")
                    src_info = f" - `{source_file}`" if source_file else ""

                    upstream_count = len(get_upstream(graph, name))
                    downstream_count = len(get_downstream(graph, name))

                    st.markdown(
                        f'<div style="background:{style["bg"]};border-left:4px solid {style["border"]};'
                        f'padding:8px 12px;margin-bottom:6px;border-radius:4px;">'
                        f'<strong>{name}</strong> <span style="color:#888">({node_type})</span>{src_info}'
                        f'<br><span style="font-size:12px;color:#666">'
                        f'{upstream_count} upstream / {downstream_count} downstream</span></div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.info(f"No tables matching '{query}'.")

        # Show root and leaf nodes
        root_col, leaf_col = st.columns(2)
        with root_col:
            st.write("**Root nodes** (no upstream):")
            for n in get_root_nodes(graph):
                st.write(f"- `{n}`")
        with leaf_col:
            st.write("**Leaf nodes** (no downstream):")
            for n in get_leaf_nodes(graph):
                st.write(f"- `{n}`")

    # --- Tab: All Tables ---
    with tab_tables:
        for layer_key in LAYER_ORDER:
            _render_layer_section(graph, layer_key, lineage)

    # --- Tab: Export ---
    with tab_export:
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
