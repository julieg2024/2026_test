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


if __name__ == "__main__":
    main()
