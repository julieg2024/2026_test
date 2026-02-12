"""Build NetworkX directed graph from lineage data."""

import networkx as nx

from data_lineage_tool.models import DataLayer, EdgeType, LineageResult, detect_layer


def build_graph(lineage: LineageResult, level: str = "table") -> nx.DiGraph:
    """
    Build a NetworkX DiGraph from lineage data.

    Args:
        lineage: Parsed lineage result.
        level: "table" for table-level only, "column" for column-level only,
               "all" for both levels.
    """
    G = nx.DiGraph()

    for name, table_node in lineage.tables.items():
        layer = detect_layer(name)
        G.add_node(
            name,
            node_type=table_node.node_type.value,
            source_file=table_node.source_file,
            level="table",
            layer=layer.value,
        )

    for edge in lineage.edges:
        if level == "table" and edge.edge_type == EdgeType.COLUMN_LINEAGE:
            continue
        if level == "column" and edge.edge_type == EdgeType.TABLE_LINEAGE:
            continue

        if edge.edge_type == EdgeType.COLUMN_LINEAGE:
            for node_id in (edge.source, edge.target):
                if node_id not in G:
                    G.add_node(node_id, node_type="column", level="column")

        G.add_edge(
            edge.source,
            edge.target,
            edge_type=edge.edge_type.value,
            transformation=edge.transformation,
            source_file=edge.source_file,
        )

    return G


def get_upstream(G: nx.DiGraph, node: str) -> set[str]:
    """Get all upstream (ancestor) nodes."""
    return nx.ancestors(G, node)


def get_downstream(G: nx.DiGraph, node: str) -> set[str]:
    """Get all downstream (descendant) nodes."""
    return nx.descendants(G, node)


def get_subgraph_for_node(G: nx.DiGraph, node: str) -> nx.DiGraph:
    """Get the subgraph containing all ancestors, descendants, and the node itself."""
    related = get_upstream(G, node) | get_downstream(G, node) | {node}
    return G.subgraph(related).copy()


def find_path(G: nx.DiGraph, source: str, target: str) -> list[str]:
    """Find the shortest directed path between two nodes.

    Returns an empty list if no path exists.
    """
    try:
        return nx.shortest_path(G, source, target)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def find_all_paths(G: nx.DiGraph, source: str, target: str) -> list[list[str]]:
    """Find all simple directed paths between two nodes.

    Returns an empty list if no path exists.
    """
    try:
        return list(nx.all_simple_paths(G, source, target))
    except nx.NodeNotFound:
        return []


def get_impact(G: nx.DiGraph, node: str) -> dict:
    """Analyze the downstream impact of changing a node.

    Returns a dict with:
      - direct: set of immediate downstream nodes
      - indirect: set of transitive downstream nodes (excluding direct)
      - total: total count of affected nodes
      - by_layer: dict mapping layer name to list of affected nodes
    """
    direct = set(G.successors(node))
    all_downstream = get_downstream(G, node)
    indirect = all_downstream - direct

    by_layer: dict[str, list[str]] = {}
    for n in sorted(all_downstream):
        layer = G.nodes[n].get("layer", "unknown")
        by_layer.setdefault(layer, []).append(n)

    return {
        "direct": direct,
        "indirect": indirect,
        "total": len(all_downstream),
        "by_layer": by_layer,
    }


def search_nodes(G: nx.DiGraph, query: str) -> list[str]:
    """Search for nodes whose name contains the query string (case-insensitive)."""
    q = query.lower()
    return sorted(n for n in G.nodes if q in n.lower())


def get_root_nodes(G: nx.DiGraph) -> list[str]:
    """Get all root nodes (nodes with no incoming edges)."""
    return sorted(n for n in G.nodes if G.in_degree(n) == 0)


def get_leaf_nodes(G: nx.DiGraph) -> list[str]:
    """Get all leaf nodes (nodes with no outgoing edges)."""
    return sorted(n for n in G.nodes if G.out_degree(n) == 0)


def to_dict(G: nx.DiGraph) -> dict:
    """Export graph as a JSON-serializable dictionary."""
    return {
        "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes],
        "edges": [
            {"source": u, "target": v, **G.edges[u, v]}
            for u, v in G.edges
        ],
    }
