"""Data models for the lineage tool."""

from dataclasses import dataclass, field
from enum import Enum


class NodeType(Enum):
    TABLE = "table"
    VIEW = "view"
    CTE = "cte"
    COLUMN = "column"


class DataLayer(Enum):
    """Logical data warehouse layer inferred from schema/table naming."""
    RAW = "raw"
    STAGING = "staging"
    MART = "mart"
    UNKNOWN = "unknown"


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


def detect_layer(table_name: str) -> DataLayer:
    """Infer the data warehouse layer from a table's schema or name prefix.

    Checks the schema prefix first (e.g. ``raw.customers``), then falls back
    to common naming conventions (e.g. ``stg_orders``, ``dim_products``).
    """
    lower = table_name.lower()

    # Schema-qualified: raw.*, staging.*, mart.*
    if "." in lower:
        schema = lower.split(".")[0]
        if schema in ("raw", "source", "src"):
            return DataLayer.RAW
        if schema in ("staging", "stg", "intermediate", "int"):
            return DataLayer.STAGING
        if schema in ("mart", "marts", "analytics", "presentation", "reporting"):
            return DataLayer.MART

    # Name-prefix conventions
    base = lower.split(".")[-1]
    if base.startswith(("raw_", "src_")):
        return DataLayer.RAW
    if base.startswith(("stg_", "staging_", "int_", "intermediate_")):
        return DataLayer.STAGING
    if base.startswith(("mart_", "dim_", "fct_", "fact_", "rpt_", "agg_")):
        return DataLayer.MART

    return DataLayer.UNKNOWN
