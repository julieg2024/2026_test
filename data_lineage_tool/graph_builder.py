"""Build NetworkX directed graph from lineage data."""

import networkx as nx

from data_lineage_tool.models import EdgeType, LineageResult


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
        G.add_node(
            name,
            node_type=table_node.node_type.value,
            source_file=table_node.source_file,
            level="table",
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


def to_dict(G: nx.DiGraph) -> dict:
    """Export graph as a JSON-serializable dictionary."""
    return {
        "nodes": [{"id": n, **G.nodes[n]} for n in G.nodes],
        "edges": [
            {"source": u, "target": v, **G.edges[u, v]}
            for u, v in G.edges
        ],
    }
