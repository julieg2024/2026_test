"""Tests for graph builder."""

from data_lineage_tool.models import (
    EdgeType, LineageEdge, LineageResult, NodeType, TableNode,
)
from data_lineage_tool.graph_builder import (
    build_graph, get_downstream, get_upstream, get_subgraph_for_node, to_dict,
)


def _make_lineage() -> LineageResult:
    """Create a simple lineage: raw -> staging -> mart."""
    return LineageResult(
        tables={
            "raw": TableNode(name="raw", node_type=NodeType.TABLE, source_file="01.sql"),
            "staging": TableNode(name="staging", node_type=NodeType.TABLE, source_file="02.sql"),
            "mart": TableNode(name="mart", node_type=NodeType.TABLE, source_file="03.sql"),
        },
        edges=[
            LineageEdge(source="raw", target="staging", edge_type=EdgeType.TABLE_LINEAGE),
            LineageEdge(source="staging", target="mart", edge_type=EdgeType.TABLE_LINEAGE),
        ],
    )


class TestBuildGraph:
    def test_nodes_created(self):
        G = build_graph(_make_lineage())
        assert "raw" in G.nodes
        assert "staging" in G.nodes
        assert "mart" in G.nodes

    def test_edges_created(self):
        G = build_graph(_make_lineage())
        assert ("raw", "staging") in G.edges
        assert ("staging", "mart") in G.edges

    def test_table_level_filters_columns(self):
        lineage = _make_lineage()
        lineage.edges.append(
            LineageEdge(source="raw.id", target="staging.id", edge_type=EdgeType.COLUMN_LINEAGE)
        )
        G = build_graph(lineage, level="table")
        assert ("raw.id", "staging.id") not in G.edges


class TestGraphQueries:
    def test_upstream(self):
        G = build_graph(_make_lineage())
        assert get_upstream(G, "mart") == {"raw", "staging"}

    def test_downstream(self):
        G = build_graph(_make_lineage())
        assert get_downstream(G, "raw") == {"staging", "mart"}

    def test_subgraph(self):
        G = build_graph(_make_lineage())
        sub = get_subgraph_for_node(G, "staging")
        assert set(sub.nodes) == {"raw", "staging", "mart"}


class TestToDict:
    def test_dict_structure(self):
        G = build_graph(_make_lineage())
        d = to_dict(G)
        assert "nodes" in d
        assert "edges" in d
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 2
