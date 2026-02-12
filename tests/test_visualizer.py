"""Tests for visualizer output."""

import json

from data_lineage_tool.models import (
    EdgeType, LineageEdge, LineageResult, NodeType, TableNode,
)
from data_lineage_tool.graph_builder import build_graph
from data_lineage_tool.visualizer import to_graphviz, to_json


def _make_graph():
    lineage = LineageResult(
        tables={
            "source": TableNode(name="source", node_type=NodeType.TABLE),
            "target": TableNode(name="target", node_type=NodeType.VIEW),
        },
        edges=[
            LineageEdge(source="source", target="target", edge_type=EdgeType.TABLE_LINEAGE),
        ],
    )
    return build_graph(lineage)


def _make_layered_graph():
    """Build a graph with nodes spanning raw, staging, and mart layers."""
    lineage = LineageResult(
        tables={
            "raw.customers": TableNode(name="raw.customers", node_type=NodeType.TABLE, source_file="01.sql"),
            "staging.stg_customers": TableNode(name="staging.stg_customers", node_type=NodeType.TABLE, source_file="05.sql"),
            "mart.customer_orders": TableNode(name="mart.customer_orders", node_type=NodeType.TABLE, source_file="08.sql"),
        },
        edges=[
            LineageEdge(source="raw.customers", target="staging.stg_customers", edge_type=EdgeType.TABLE_LINEAGE),
            LineageEdge(source="staging.stg_customers", target="mart.customer_orders", edge_type=EdgeType.TABLE_LINEAGE),
        ],
    )
    return build_graph(lineage)


class TestGraphviz:
    def test_dot_output(self):
        G = _make_graph()
        dot = to_graphviz(G)
        assert "digraph lineage" in dot
        assert "source" in dot
        assert "target" in dot
        assert "->" in dot

    def test_view_shape(self):
        G = _make_graph()
        dot = to_graphviz(G)
        assert "parallelogram" in dot

    def test_layer_clusters(self):
        G = _make_layered_graph()
        dot = to_graphviz(G)
        assert "subgraph cluster_raw" in dot
        assert "subgraph cluster_staging" in dot
        assert "subgraph cluster_mart" in dot

    def test_layer_labels(self):
        G = _make_layered_graph()
        dot = to_graphviz(G)
        assert "Raw  /  Source" in dot
        assert "Staging  /  Intermediate" in dot
        assert "Mart  /  Analytics" in dot

    def test_no_empty_clusters(self):
        """Layers with no nodes should not appear as clusters."""
        lineage = LineageResult(
            tables={
                "raw.orders": TableNode(name="raw.orders", node_type=NodeType.TABLE),
            },
            edges=[],
        )
        G = build_graph(lineage)
        dot = to_graphviz(G)
        assert "cluster_raw" in dot
        assert "cluster_staging" not in dot
        assert "cluster_mart" not in dot


class TestJson:
    def test_json_valid(self):
        G = _make_graph()
        json_str = to_json(G)
        data = json.loads(json_str)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    def test_json_file_output(self, tmp_path):
        G = _make_graph()
        out_file = str(tmp_path / "test.json")
        to_json(G, output_path=out_file)
        with open(out_file) as f:
            data = json.load(f)
        assert len(data["nodes"]) == 2

    def test_json_contains_layer(self):
        G = _make_layered_graph()
        json_str = to_json(G)
        data = json.loads(json_str)
        layers = {n["layer"] for n in data["nodes"]}
        assert layers == {"raw", "staging", "mart"}
