"""Generate static visualizations: Graphviz and JSON."""

import json
from collections import defaultdict
from pathlib import Path

import networkx as nx

from data_lineage_tool.graph_builder import to_dict


# --- Layer styling ---

# Ordered from left (source) to right (consumption) for the hierarchy.
LAYER_ORDER = ["raw", "staging", "mart", "unknown"]

LAYER_STYLES = {
    "raw": {
        "label": "Raw  /  Source",
        "bg": "#EBF5FB",
        "border": "#2E86C1",
        "node_fill": "#2E86C1",
    },
    "staging": {
        "label": "Staging  /  Intermediate",
        "bg": "#FEF9E7",
        "border": "#F39C12",
        "node_fill": "#F39C12",
    },
    "mart": {
        "label": "Mart  /  Analytics",
        "bg": "#EAFAF1",
        "border": "#27AE60",
        "node_fill": "#27AE60",
    },
    "unknown": {
        "label": "Other",
        "bg": "#F4F6F7",
        "border": "#95A5A6",
        "node_fill": "#95A5A6",
    },
}


# --- Graphviz ---

def to_graphviz(G: nx.DiGraph) -> str:
    """Generate DOT language representation with layer-based subgraph clusters."""
    lines = [
        "digraph lineage {",
        '    rankdir=LR;',
        "    compound=true;",
        "    newrank=true;",
        '    node [shape=box, style="filled,rounded", fontname="Helvetica", fontsize=11, margin="0.2,0.1"];',
        '    edge [fontname="Helvetica", fontsize=9, color="#888888", arrowsize=0.8];',
        "",
    ]

    # Group nodes by layer
    layer_nodes: dict[str, list[str]] = defaultdict(list)
    for node in G.nodes:
        layer = G.nodes[node].get("layer", "unknown")
        layer_nodes[layer].append(node)

    # Emit each layer as a DOT subgraph cluster
    for layer in LAYER_ORDER:
        nodes = layer_nodes.get(layer)
        if not nodes:
            continue
        style = LAYER_STYLES[layer]
        lines.append(f"    subgraph cluster_{layer} {{")
        lines.append(f'        label="{style["label"]}";')
        lines.append(f'        style="filled,rounded";')
        lines.append(f'        fillcolor="{style["bg"]}";')
        lines.append(f'        color="{style["border"]}";')
        lines.append(f'        penwidth=2;')
        lines.append(f'        fontname="Helvetica Bold";')
        lines.append(f'        fontsize=13;')
        lines.append(f'        labeljust=l;')
        lines.append("")

        for node in sorted(nodes):
            node_data = G.nodes[node]
            node_type = node_data.get("node_type", "table")
            fill = style["node_fill"]
            shape = "parallelogram" if node_type == "view" else "box"
            dot_id = _dot_id(node)
            lines.append(
                f'        {dot_id} [label="{node}", fillcolor="{fill}", '
                f'fontcolor="white", shape={shape}];'
            )

        lines.append("    }")
        lines.append("")

    # Enforce left-to-right ordering between layer clusters via invisible edges
    present_layers = [l for l in LAYER_ORDER if layer_nodes.get(l)]
    for i in range(len(present_layers) - 1):
        left_layer = present_layers[i]
        right_layer = present_layers[i + 1]
        left_node = sorted(layer_nodes[left_layer])[0]
        right_node = sorted(layer_nodes[right_layer])[0]
        lines.append(
            f"    {_dot_id(left_node)} -> {_dot_id(right_node)} "
            f"[style=invis, weight=10];"
        )
    if present_layers:
        lines.append("")

    # Edges
    for u, v in G.edges:
        edge_data = G.edges[u, v]
        transform = edge_data.get("transformation", "")
        attrs = []
        if transform:
            attrs.append(f'label="{transform}"')
        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f"    {_dot_id(u)} -> {_dot_id(v)}{attr_str};")

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
