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
