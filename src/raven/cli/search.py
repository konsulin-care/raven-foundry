"""Search command for Raven CLI."""

from pathlib import Path
from typing import Optional

import click

from raven.ingestion import DEFAULT_SORT_ORDER, format_search_result, search_works
from raven.storage import search_papers


def _resolve_db_path(
    env_path: Optional[Path] = None, db_path: Optional[Path] = None
) -> Path:
    """Resolve database path with proper precedence."""
    from raven.config import _get_data_dir, _load_config

    _load_config(env_path)

    if db_path is not None:
        return db_path

    return _get_data_dir() / "raven.db"


def _display_results(results: list) -> None:
    """Display search results with formatting."""
    for i, work in enumerate(results, 1):
        formatted = format_search_result(work)
        _print_formatted_result(i, formatted)


def _print_formatted_result(index: int, formatted: dict) -> None:
    """Print a single formatted result."""
    click.echo(f"{index}. {formatted['title']}")
    click.echo(f"   Identifier: {formatted.get('identifier') or 'N/A'}")
    click.echo(f"   Year: {formatted.get('publication_year', 'N/A')}")
    click.echo(f"   Type: {formatted['type']}")
    click.echo(f"   Citations: {formatted.get('cited_by_count', 0)}")
    click.echo(f"   Open Access: {'Yes' if formatted.get('open_access') else 'No'}")
    if formatted.get("relevance_score"):
        click.echo(f"   Relevance: {formatted['relevance_score']:.3f}")
    _print_abstract(formatted)
    click.echo("---")


def _print_abstract(formatted: dict) -> None:
    """Print abstract preview if available."""
    if formatted.get("abstract"):
        abstract_preview = formatted["abstract"][:300]
        if len(formatted["abstract"]) > 300:
            abstract_preview += "..."
        click.echo(f"   Abstract: {abstract_preview}")


def _search_local(db_path: Path, query: str) -> None:
    """Search local database and display results."""
    results = search_papers(db_path, query)

    if not results:
        click.echo("No results found in local database.")
        return

    for paper in results:
        click.echo(f"Title: {paper['title']}")
        click.echo(f"Identifier: {paper.get('identifier') or 'N/A'}")
        click.echo(f"Type: {paper['type']}")
        click.echo("---")


def _search_openalex(
    query: str,
    filter_str: Optional[str],
    page: int,
    per_page: int,
    sort: str,
    use_semantic: bool,
) -> None:
    """Search OpenAlex and display results."""
    result_data = search_works(
        query=query,
        filter_str=filter_str,
        page=page,
        per_page=per_page,
        sort=sort,
        use_semantic=use_semantic,
    )

    results = result_data.get("results", [])
    meta = result_data.get("meta", {})
    search_type = result_data.get("search_type", "unknown")

    if not results:
        click.echo("No results found.")
        return

    click.echo(f"Search type: {search_type}")
    click.echo(f"Total results: {meta.get('count', 'unknown')}")
    click.echo(f"Page: {page} of ~{(meta.get('count', 0) // per_page) + 1}")
    click.echo("---")

    _display_results(results)

    click.echo("To ingest a paper, run:")
    click.echo("  raven ingest <identifier>  # DOI, OpenAlex ID, PMID, or MAG")
    click.echo("Examples:")
    click.echo("  raven ingest 10.5281/zenodo.18201069")
    click.echo("  raven ingest W7119934875")
    click.echo("  raven ingest pmid:29456894")


@click.command()
@click.argument("query")
@click.option(
    "--db",
    "-d",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Path to the database file (overrides env-derived path)",
)
@click.option(
    "--env",
    "-e",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="Path to .env file",
)
@click.option(
    "--filter",
    "-f",
    "filter_str",
    default=None,
    help="Additional OpenAlex filters (e.g., publication_year:>2020,type:article)",
)
@click.option(
    "--page",
    "-p",
    default=1,
    type=int,
    help="Page number for pagination",
)
@click.option(
    "--per-page",
    default=50,
    type=int,
    help="Results per page (max 100 for keyword, 50 for semantic)",
)
@click.option(
    "--sort",
    default=DEFAULT_SORT_ORDER,
    help="Sort order in OpenAlex format (e.g., 'publication_year:desc,relevance_score:desc')",
)
@click.option(
    "--local",
    is_flag=True,
    default=False,
    help="Search local database instead of OpenAlex",
)
@click.option(
    "--semantic/--keyword",
    "use_semantic",
    default=True,
    help="Search mode: semantic (default) or keyword only",
)
def search(
    query: str,
    db: Optional[Path],
    env: Optional[Path],
    filter_str: Optional[str],
    page: int,
    per_page: int,
    sort: str,
    use_semantic: bool,
    local: bool,
) -> None:
    """Search publications by query string.

    Uses OpenAlex semantic search by default (with keyword fallback).
    Set --local to search local database instead.

    Examples:
        raven search "machine learning in healthcare"
        raven search "AI" --filter "publication_year:>2020" --page 2
        raven search "dna methylation" --keyword  # Force keyword search
        raven search "neur*" --local  # Local DB search
    """
    db_path = _resolve_db_path(env, db)

    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    if local:
        _search_local(db_path, query)
    else:
        _search_openalex(query, filter_str, page, per_page, sort, use_semantic)
