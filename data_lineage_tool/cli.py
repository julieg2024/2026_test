"""CLI entry point for the data lineage tool."""

from pathlib import Path

import click


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Data Lineage Tool - trace data flow through SQL."""
    pass


@main.command()
@click.argument("source")
@click.option("--branch", "-b", default=None, help="Git branch to clone")
@click.option("--dialect", "-d", default=None, help="SQL dialect (e.g. bigquery, snowflake)")
@click.option(
    "--level", "-l", default="table",
    type=click.Choice(["table", "column", "all"]),
    help="Lineage granularity level",
)
@click.option("--output-dir", "-o", default="./lineage_output", help="Output directory")
@click.option(
    "--format", "-f", "formats", multiple=True,
    default=["graphviz", "json"],
    type=click.Choice(["graphviz", "json"]),
    help="Output formats",
)
@click.option("--focus", default=None, help="Focus on a specific table")
def analyze(source, branch, dialect, level, output_dir, formats, focus):
    """Analyze SQL files and generate lineage visualization."""
    from data_lineage_tool.github_connector import resolve_source
    from data_lineage_tool.sql_scanner import scan_directory
    from data_lineage_tool.sql_parser import parse_sql_files
    from data_lineage_tool.graph_builder import build_graph, get_subgraph_for_node
    from data_lineage_tool import visualizer

    click.echo(f"Resolving source: {source}")
    repo_path = resolve_source(source, branch=branch)

    sql_files = scan_directory(repo_path)
    click.echo(f"Found {len(sql_files)} SQL files")
    if not sql_files:
        click.echo("No SQL files found. Exiting.")
        return

    click.echo("Parsing SQL files...")
    lineage = parse_sql_files(sql_files, dialect=dialect)
    click.echo(f"Found {len(lineage.tables)} tables/views, {len(lineage.edges)} lineage edges")

    graph = build_graph(lineage, level=level)

    if focus:
        if focus not in graph:
            click.echo(f"Table '{focus}' not found in lineage graph.")
            return
        graph = get_subgraph_for_node(graph, focus)
        click.echo(f"Focused on '{focus}': {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if "graphviz" in formats:
        visualizer.save_graphviz(graph, str(out / "lineage.png"))
        click.echo(f"Graphviz PNG: {out / 'lineage.png'}")

    if "json" in formats:
        visualizer.to_json(graph, str(out / "lineage.json"))
        click.echo(f"JSON export: {out / 'lineage.json'}")

    click.echo("Done!")


@main.command()
@click.argument("source")
@click.option("--dialect", "-d", default=None, help="SQL dialect")
def list_tables(source, dialect):
    """List all tables found in the SQL files."""
    from data_lineage_tool.github_connector import resolve_source
    from data_lineage_tool.sql_scanner import scan_directory
    from data_lineage_tool.sql_parser import parse_sql_files

    repo_path = resolve_source(source)
    sql_files = scan_directory(repo_path)
    lineage = parse_sql_files(sql_files, dialect=dialect)

    for name, table in sorted(lineage.tables.items()):
        source_info = f"  ({table.source_file})" if table.source_file else ""
        click.echo(f"  {table.node_type.value:6s}  {name}{source_info}")


@main.command()
@click.argument("source")
@click.argument("table")
@click.option("--branch", "-b", default=None, help="Git branch to clone")
@click.option("--dialect", "-d", default=None, help="SQL dialect")
def impact(source, table, branch, dialect):
    """Show the downstream impact of changing a table."""
    from data_lineage_tool.github_connector import resolve_source
    from data_lineage_tool.sql_scanner import scan_directory
    from data_lineage_tool.sql_parser import parse_sql_files
    from data_lineage_tool.graph_builder import build_graph, get_impact

    repo_path = resolve_source(source, branch=branch)
    sql_files = scan_directory(repo_path)
    lineage = parse_sql_files(sql_files, dialect=dialect)
    graph = build_graph(lineage, level="table")

    if table not in graph:
        click.echo(f"Table '{table}' not found in lineage graph.")
        return

    result = get_impact(graph, table)
    click.echo(f"\nImpact analysis for: {table}")
    click.echo(f"Total affected: {result['total']} table(s)\n")

    if result["direct"]:
        click.echo("Direct dependents:")
        for n in sorted(result["direct"]):
            click.echo(f"  - {n}")

    if result["indirect"]:
        click.echo("\nIndirect dependents:")
        for n in sorted(result["indirect"]):
            click.echo(f"  - {n}")

    if result["by_layer"]:
        click.echo("\nBy layer:")
        for layer, nodes in sorted(result["by_layer"].items()):
            click.echo(f"  {layer}: {', '.join(nodes)}")


@main.command()
@click.argument("source")
@click.argument("from_table")
@click.argument("to_table")
@click.option("--branch", "-b", default=None, help="Git branch to clone")
@click.option("--dialect", "-d", default=None, help="SQL dialect")
@click.option("--all-paths", is_flag=True, help="Show all paths, not just shortest")
def trace(source, from_table, to_table, branch, dialect, all_paths):
    """Trace the data flow path between two tables."""
    from data_lineage_tool.github_connector import resolve_source
    from data_lineage_tool.sql_scanner import scan_directory
    from data_lineage_tool.sql_parser import parse_sql_files
    from data_lineage_tool.graph_builder import build_graph, find_path, find_all_paths

    repo_path = resolve_source(source, branch=branch)
    sql_files = scan_directory(repo_path)
    lineage = parse_sql_files(sql_files, dialect=dialect)
    graph = build_graph(lineage, level="table")

    for t in (from_table, to_table):
        if t not in graph:
            click.echo(f"Table '{t}' not found in lineage graph.")
            return

    if all_paths:
        paths = find_all_paths(graph, from_table, to_table)
        if not paths:
            click.echo(f"No path found from '{from_table}' to '{to_table}'.")
            return
        click.echo(f"\nAll paths from {from_table} to {to_table} ({len(paths)} found):\n")
        for i, p in enumerate(paths, 1):
            click.echo(f"  Path {i}: {' -> '.join(p)}")
    else:
        path = find_path(graph, from_table, to_table)
        if not path:
            click.echo(f"No path found from '{from_table}' to '{to_table}'.")
            return
        click.echo(f"\nShortest path from {from_table} to {to_table}:\n")
        click.echo(f"  {' -> '.join(path)}")


if __name__ == "__main__":
    main()
