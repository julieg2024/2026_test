"""Data models for the lineage tool."""

from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    TABLE = "table"
    VIEW = "view"
    CTE = "cte"
    COLUMN = "column"


class EdgeType(Enum):
    TABLE_LINEAGE = "table_lineage"
    COLUMN_LINEAGE = "column_lineage"


@dataclass
class TableNode:
    """Represents a table, view, or CTE in the lineage graph."""
    name: str
    node_type: NodeType
    source_file: str = ""
    columns: list[str] = field(default_factory=list)


@dataclass
class ColumnNode:
    """Represents a column within a table."""
    table: str
    column: str

    @property
    def fqn(self) -> str:
        return f"{self.table}.{self.column}"


@dataclass
class LineageEdge:
    """A directed edge representing data flow: source -> target."""
    source: str
    target: str
    edge_type: EdgeType
    transformation: str = ""
    source_file: str = ""


@dataclass
class LineageResult:
    """Aggregated lineage output from parsing all SQL files."""
    tables: dict[str, TableNode] = field(default_factory=dict)
    edges: list[LineageEdge] = field(default_factory=list)
