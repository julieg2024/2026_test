"""Tests for graph builder."""

from data_lineage_tool.models import (
    EdgeType, LineageEdge, LineageResult, NodeType, TableNode,
)
from data_lineage_tool.graph_builder import (
    build_graph, find_all_paths, find_path, get_downstream, get_impact,
    get_leaf_nodes, get_root_nodes, get_subgraph_for_node, get_upstream,
    search_nodes, to_dict,
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


class TestFindPath:
    def test_shortest_path(self):
        G = build_graph(_make_lineage())
        path = find_path(G, "raw", "mart")
        assert path == ["raw", "staging", "mart"]

    def test_direct_path(self):
        G = build_graph(_make_lineage())
        path = find_path(G, "raw", "staging")
        assert path == ["raw", "staging"]

    def test_no_path(self):
        G = build_graph(_make_lineage())
        path = find_path(G, "mart", "raw")
        assert path == []

    def test_nonexistent_node(self):
        G = build_graph(_make_lineage())
        path = find_path(G, "raw", "nonexistent")
        assert path == []

    def test_all_paths(self):
        G = build_graph(_make_lineage())
        paths = find_all_paths(G, "raw", "mart")
        assert len(paths) >= 1
        assert ["raw", "staging", "mart"] in paths

    def test_all_paths_no_path(self):
        G = build_graph(_make_lineage())
        paths = find_all_paths(G, "mart", "raw")
        assert paths == []


class TestImpact:
    def test_impact_from_root(self):
        G = build_graph(_make_lineage())
        result = get_impact(G, "raw")
        assert result["total"] == 2
        assert result["direct"] == {"staging"}
        assert result["indirect"] == {"mart"}

    def test_impact_from_leaf(self):
        G = build_graph(_make_lineage())
        result = get_impact(G, "mart")
        assert result["total"] == 0
        assert result["direct"] == set()
        assert result["indirect"] == set()

    def test_impact_by_layer(self):
        G = build_graph(_make_lineage())
        result = get_impact(G, "raw")
        assert "by_layer" in result


class TestSearchNodes:
    def test_search_finds_match(self):
        G = build_graph(_make_lineage())
        results = search_nodes(G, "stag")
        assert "staging" in results

    def test_search_case_insensitive(self):
        G = build_graph(_make_lineage())
        results = search_nodes(G, "RAW")
        assert "raw" in results

    def test_search_no_match(self):
        G = build_graph(_make_lineage())
        results = search_nodes(G, "nonexistent")
        assert results == []


class TestRootLeafNodes:
    def test_root_nodes(self):
        G = build_graph(_make_lineage())
        roots = get_root_nodes(G)
        assert roots == ["raw"]

    def test_leaf_nodes(self):
        G = build_graph(_make_lineage())
        leaves = get_leaf_nodes(G)
        assert leaves == ["mart"]


class TestToDict:
    def test_dict_structure(self):
        G = build_graph(_make_lineage())
        d = to_dict(G)
        assert "nodes" in d
        assert "edges" in d
        assert len(d["nodes"]) == 3
        assert len(d["edges"]) == 2
