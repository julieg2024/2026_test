"""Generate static visualizations: Graphviz and JSON."""

import json
from pathlib import Path

import networkx as nx

from data_lineage_tool.graph_builder import to_dict


# --- Graphviz ---

def to_graphviz(G: nx.DiGraph) -> str:
    """Generate DOT language representation of the graph."""
    lines = [
        "digraph lineage {",
        '    rankdir=LR;',
        '    node [shape=box, style=filled, fontname="Helvetica"];',
        '    edge [fontname="Helvetica", fontsize=10];',
    ]

    color_map = {
        "table": "#4A90D9",
        "view": "#7B68EE",
        "column": "#50C878",
        "cte": "#FFB347",
    }

    for node in G.nodes:
        node_data = G.nodes[node]
        node_type = node_data.get("node_type", "table")
        color = color_map.get(node_type, "#999999")
        shape = "parallelogram" if node_type == "view" else "box"
        dot_id = _dot_id(node)
        lines.append(
            f'    {dot_id} [label="{node}", fillcolor="{color}", '
            f'fontcolor="white", shape={shape}];'
        )

    for u, v in G.edges:
        edge_data = G.edges[u, v]
        transform = edge_data.get("transformation", "")
        label = f' [label="{transform}"]' if transform else ""
        lines.append(f"    {_dot_id(u)} -> {_dot_id(v)}{label};")

    lines.append("}")
    return "\n".join(lines)


def save_graphviz(G: nx.DiGraph, output_path: str, format: str = "png") -> None:
    """Render graph using Graphviz and save to file."""
    import graphviz as gv

    dot_source = to_graphviz(G)
    src = gv.Source(dot_source)
    # graphviz render removes the extension automatically, so strip it
    out_path = Path(output_path)
    src.render(
        filename=str(out_path.with_suffix("")),
        format=format,
        cleanup=True,
    )


def _dot_id(name: str) -> str:
    """Sanitize node name for DOT format."""
    return '"' + name.replace('"', '\\"') + '"'


# --- JSON ---

def to_json(G: nx.DiGraph, output_path: str | None = None) -> str:
    """Export graph as JSON. Optionally save to file."""
    data = to_dict(G)
    json_str = json.dumps(data, indent=2)
    if output_path:
        Path(output_path).write_text(json_str)
    return json_str
