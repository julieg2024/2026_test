"""Parse SQL files and extract data lineage using SQLGlot."""

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.scope import build_scope, traverse_scope

from data_lineage_tool.models import (
    EdgeType,
    LineageEdge,
    LineageResult,
    NodeType,
    TableNode,
)
from data_lineage_tool.sql_scanner import SQLFile


def parse_sql_files(
    sql_files: list[SQLFile],
    dialect: str | None = None,
) -> LineageResult:
    """Parse all SQL files and return aggregated lineage."""
    result = LineageResult()
    for sql_file in sql_files:
        _parse_single_file(sql_file, result, dialect)
    return result


def _parse_single_file(
    sql_file: SQLFile,
    result: LineageResult,
    dialect: str | None,
) -> None:
    """Parse one SQL file (may contain multiple statements)."""
    try:
        statements = sqlglot.parse(
            sql_file.content,
            dialect=dialect,
            error_level=sqlglot.ErrorLevel.WARN,
        )
    except Exception:
        return

    for stmt in statements:
        if stmt is None:
            continue
        _extract_from_statement(stmt, sql_file, result)


def _extract_from_statement(
    stmt: exp.Expression,
    sql_file: SQLFile,
    result: LineageResult,
) -> None:
    """Dispatch lineage extraction based on statement type."""
    if isinstance(stmt, exp.Create):
        _handle_create(stmt, sql_file, result)
    elif isinstance(stmt, exp.Insert):
        _handle_insert(stmt, sql_file, result)
    elif isinstance(stmt, exp.Select):
        _extract_source_tables(stmt, sql_file, result, target=None)


def _handle_create(
    stmt: exp.Create,
    sql_file: SQLFile,
    result: LineageResult,
) -> None:
    """Handle CREATE TABLE AS SELECT and CREATE VIEW AS SELECT."""
    target_table_expr = stmt.find(exp.Table)
    if target_table_expr is None:
        return

    target_name = _table_name(target_table_expr)
    kind = (stmt.args.get("kind") or "").upper()
    node_type = NodeType.VIEW if "VIEW" in kind else NodeType.TABLE

    result.tables[target_name] = TableNode(
        name=target_name,
        node_type=node_type,
        source_file=sql_file.relative_path,
    )

    select_expr = stmt.expression
    if select_expr and isinstance(select_expr, (exp.Select, exp.Union)):
        select_to_parse = select_expr
        if isinstance(select_expr, exp.Union):
            # For UNION, process both sides
            for part in [select_expr.left, select_expr.right]:
                if isinstance(part, exp.Select):
                    _extract_source_tables(part, sql_file, result, target=target_name)
                    _extract_column_lineage(part, sql_file, result, target=target_name)
            return

        _extract_source_tables(select_to_parse, sql_file, result, target=target_name)
        _extract_column_lineage(select_to_parse, sql_file, result, target=target_name)


def _handle_insert(
    stmt: exp.Insert,
    sql_file: SQLFile,
    result: LineageResult,
) -> None:
    """Handle INSERT INTO ... SELECT."""
    target_table_expr = stmt.find(exp.Table)
    if target_table_expr is None:
        return

    target_name = _table_name(target_table_expr)
    result.tables.setdefault(target_name, TableNode(
        name=target_name,
        node_type=NodeType.TABLE,
        source_file=sql_file.relative_path,
    ))

    select_expr = stmt.expression
    if select_expr and isinstance(select_expr, (exp.Select, exp.Union)):
        if isinstance(select_expr, exp.Union):
            for part in [select_expr.left, select_expr.right]:
                if isinstance(part, exp.Select):
                    _extract_source_tables(part, sql_file, result, target=target_name)
                    _extract_column_lineage(part, sql_file, result, target=target_name)
            return

        _extract_source_tables(select_expr, sql_file, result, target=target_name)
        _extract_column_lineage(select_expr, sql_file, result, target=target_name)


def _extract_source_tables(
    select: exp.Select,
    sql_file: SQLFile,
    result: LineageResult,
    target: str | None,
) -> None:
    """Extract all source tables from a SELECT, filtering out CTE aliases."""
    cte_names = set()
    for cte in select.find_all(exp.CTE):
        if cte.alias:
            cte_names.add(cte.alias)

    # Try scope-based traversal first (more accurate)
    try:
        root_scope = build_scope(select)
        if root_scope:
            # Include root scope itself (traverse_scope only yields children)
            all_scopes = [root_scope] + list(traverse_scope(root_scope))
            found_any = False
            for scope in all_scopes:
                for source in scope.sources.values():
                    if isinstance(source, exp.Table):
                        name = _table_name(source)
                        if name not in cte_names:
                            _add_source_table(name, sql_file, result, target)
                            found_any = True
            if found_any:
                return
    except Exception:
        pass

    # Fallback: simple find_all
    for table in select.find_all(exp.Table):
        name = _table_name(table)
        if name not in cte_names:
            _add_source_table(name, sql_file, result, target)


def _add_source_table(
    source_name: str,
    sql_file: SQLFile,
    result: LineageResult,
    target: str | None,
) -> None:
    """Register a source table and create a lineage edge to target if given."""
    result.tables.setdefault(source_name, TableNode(
        name=source_name,
        node_type=NodeType.TABLE,
    ))
    if target:
        result.edges.append(LineageEdge(
            source=source_name,
            target=target,
            edge_type=EdgeType.TABLE_LINEAGE,
            source_file=sql_file.relative_path,
        ))


def _extract_column_lineage(
    select: exp.Select,
    sql_file: SQLFile,
    result: LineageResult,
    target: str,
) -> None:
    """Extract column-level lineage from SELECT expressions."""
    for sel_expr in select.selects:
        target_col_name = sel_expr.alias_or_name
        if not target_col_name or target_col_name == "*":
            continue

        target_fqn = f"{target}.{target_col_name}"

        for col_ref in sel_expr.find_all(exp.Column):
            source_table = col_ref.table or ""
            source_col = col_ref.name
            source_fqn = f"{source_table}.{source_col}" if source_table else source_col

            result.edges.append(LineageEdge(
                source=source_fqn,
                target=target_fqn,
                edge_type=EdgeType.COLUMN_LINEAGE,
                transformation=_get_transformation(sel_expr),
                source_file=sql_file.relative_path,
            ))


def _get_transformation(expr: exp.Expression) -> str:
    """Extract a short description of the transformation applied."""
    if isinstance(expr, exp.Column):
        return ""
    if isinstance(expr, exp.Alias):
        inner = expr.this
        if isinstance(inner, exp.Column):
            return ""
        if isinstance(inner, exp.Func):
            return type(inner).__name__.upper()
    return ""


def _table_name(table: exp.Table) -> str:
    """Build qualified table name from a Table expression."""
    parts = []
    if table.catalog:
        parts.append(table.catalog)
    if table.db:
        parts.append(table.db)
    parts.append(table.name)
    return ".".join(parts)
