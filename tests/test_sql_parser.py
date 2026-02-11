"""Tests for SQL parser lineage extraction."""

from pathlib import Path

from data_lineage_tool.models import EdgeType, NodeType
from data_lineage_tool.sql_parser import parse_sql_files
from data_lineage_tool.sql_scanner import SQLFile


def _make_sql_file(content: str, name: str = "test.sql") -> list[SQLFile]:
    return [SQLFile(path=Path(name), relative_path=name, content=content)]


class TestCreateTableAsSelect:
    def test_basic_ctas(self):
        sql = "CREATE TABLE target AS SELECT a, b FROM source"
        result = parse_sql_files(_make_sql_file(sql))
        assert "target" in result.tables
        assert "source" in result.tables
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        assert any(e.source == "source" and e.target == "target" for e in table_edges)

    def test_ctas_with_schema(self):
        sql = "CREATE TABLE staging.stg_orders AS SELECT id FROM raw.orders"
        result = parse_sql_files(_make_sql_file(sql))
        assert "staging.stg_orders" in result.tables
        assert "raw.orders" in result.tables

    def test_ctas_with_join(self):
        sql = """
        CREATE TABLE output_tbl AS
        SELECT a.x, b.y
        FROM tbl_a a
        JOIN tbl_b b ON a.id = b.id
        """
        result = parse_sql_files(_make_sql_file(sql))
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        sources = {e.source for e in table_edges if e.target == "output_tbl"}
        assert "tbl_a" in sources
        assert "tbl_b" in sources


class TestCreateView:
    def test_basic_view(self):
        sql = "CREATE VIEW my_view AS SELECT * FROM base_table"
        result = parse_sql_files(_make_sql_file(sql))
        assert "my_view" in result.tables
        assert result.tables["my_view"].node_type == NodeType.VIEW
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        assert any(e.source == "base_table" and e.target == "my_view" for e in table_edges)


class TestInsertIntoSelect:
    def test_basic_insert(self):
        sql = "INSERT INTO target SELECT x, y FROM source"
        result = parse_sql_files(_make_sql_file(sql))
        assert "target" in result.tables
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        assert any(e.source == "source" and e.target == "target" for e in table_edges)


class TestCTEHandling:
    def test_cte_not_treated_as_source(self):
        sql = """
        CREATE TABLE final AS
        WITH cte AS (SELECT a FROM raw_table)
        SELECT a FROM cte
        """
        result = parse_sql_files(_make_sql_file(sql))
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        sources = {e.source for e in table_edges if e.target == "final"}
        assert "raw_table" in sources
        assert "cte" not in sources

    def test_multiple_ctes(self):
        sql = """
        CREATE TABLE result AS
        WITH
            cte1 AS (SELECT a FROM table_a),
            cte2 AS (SELECT b FROM table_b)
        SELECT cte1.a, cte2.b FROM cte1 JOIN cte2 ON cte1.a = cte2.b
        """
        result = parse_sql_files(_make_sql_file(sql))
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        sources = {e.source for e in table_edges if e.target == "result"}
        assert "table_a" in sources
        assert "table_b" in sources
        assert "cte1" not in sources
        assert "cte2" not in sources

    def test_nested_ctes_with_joins(self):
        """Nested CTEs where CTEs reference real tables and join each other."""
        sql = """
        CREATE TABLE mart.customer_lifetime_segments AS
        WITH order_totals AS (
            SELECT customer_id, order_id, SUM(quantity * unit_price) AS order_total
            FROM staging.stg_order_items
            GROUP BY customer_id, order_id
        ),
        customer_metrics AS (
            SELECT ot.customer_id, COUNT(DISTINCT ot.order_id) AS num_orders,
                   SUM(ot.order_total) AS lifetime_value
            FROM order_totals ot
            JOIN staging.stg_orders o ON ot.customer_id = o.customer_id
            GROUP BY ot.customer_id
        ),
        segmented AS (
            SELECT cm.customer_id, cm.num_orders, cm.lifetime_value,
                   CASE WHEN cm.lifetime_value >= 1000 THEN 'platinum' ELSE 'bronze' END AS segment
            FROM customer_metrics cm
            JOIN staging.stg_customers c ON cm.customer_id = c.customer_id
        )
        SELECT customer_id, num_orders, lifetime_value, segment
        FROM segmented
        """
        result = parse_sql_files(_make_sql_file(sql))

        assert "mart.customer_lifetime_segments" in result.tables

        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        sources = {e.source for e in table_edges if e.target == "mart.customer_lifetime_segments"}

        # Real source tables should be detected
        assert "staging.stg_order_items" in sources
        assert "staging.stg_orders" in sources
        assert "staging.stg_customers" in sources

        # CTE aliases should NOT appear as source tables
        assert "order_totals" not in sources
        assert "customer_metrics" not in sources
        assert "segmented" not in sources

    def test_cte_from_sample_fixture(self):
        """Parse the sample CTE fixture file end-to-end."""
        fixture = Path(__file__).parent / "fixtures" / "11_mart_customer_lifetime_segments.sql"
        content = fixture.read_text()
        result = parse_sql_files(_make_sql_file(content, name="11_mart_customer_lifetime_segments.sql"))

        assert "mart.customer_lifetime_segments" in result.tables

        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        sources = {e.source for e in table_edges if e.target == "mart.customer_lifetime_segments"}

        assert "staging.stg_order_items" in sources
        assert "staging.stg_orders" in sources
        assert "staging.stg_customers" in sources

        for cte_name in ("order_totals", "customer_metrics", "segmented"):
            assert cte_name not in sources


class TestMultiStatement:
    def test_chained_lineage(self):
        sql = """
        CREATE TABLE staging AS SELECT * FROM raw;
        CREATE TABLE final AS SELECT * FROM staging;
        """
        result = parse_sql_files(_make_sql_file(sql))
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        assert any(e.source == "raw" and e.target == "staging" for e in table_edges)
        assert any(e.source == "staging" and e.target == "final" for e in table_edges)


class TestColumnLineage:
    def test_column_edges_created(self):
        sql = "CREATE TABLE target AS SELECT a, b FROM source"
        result = parse_sql_files(_make_sql_file(sql))
        col_edges = [e for e in result.edges if e.edge_type == EdgeType.COLUMN_LINEAGE]
        assert len(col_edges) > 0

    def test_column_with_alias(self):
        sql = "CREATE TABLE target AS SELECT a AS renamed_a FROM source"
        result = parse_sql_files(_make_sql_file(sql))
        col_edges = [e for e in result.edges if e.edge_type == EdgeType.COLUMN_LINEAGE]
        targets = {e.target for e in col_edges}
        assert "target.renamed_a" in targets


class TestSubquery:
    def test_subquery_source(self):
        sql = "CREATE TABLE output_tbl AS SELECT * FROM (SELECT id FROM inner_tbl) sub"
        result = parse_sql_files(_make_sql_file(sql))
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        sources = {e.source for e in table_edges if e.target == "output_tbl"}
        assert "inner_tbl" in sources


class TestDDLOnly:
    def test_plain_create_table(self):
        sql = """
        CREATE TABLE raw.customers (
            id INTEGER PRIMARY KEY,
            name VARCHAR(100)
        )
        """
        result = parse_sql_files(_make_sql_file(sql))
        assert "raw.customers" in result.tables
        # No lineage edges for DDL-only
        table_edges = [e for e in result.edges if e.edge_type == EdgeType.TABLE_LINEAGE]
        assert len(table_edges) == 0


class TestErrorHandling:
    def test_invalid_sql_skipped(self):
        sql = "THIS IS NOT VALID SQL AT ALL ;;;"
        result = parse_sql_files(_make_sql_file(sql))
        # Should not raise, may have empty or partial results
        assert isinstance(result.tables, dict)

    def test_empty_file(self):
        result = parse_sql_files([])
        assert len(result.tables) == 0
        assert len(result.edges) == 0
