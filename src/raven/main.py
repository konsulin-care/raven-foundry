"""CLI entry point for Raven - offline-first research system."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from raven.config import _get_data_dir, _load_config
from raven.embeddings import clean_model_cache, get_model_cache_size

# Configure logging to show INFO level messages in CLI
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    stream=sys.stderr,
)


def _get_version() -> str:
    """Get version from package metadata, default to dev if not installed."""
    try:
        from importlib.metadata import version

        return version("raven-foundry")
    except Exception:
        return "dev"


def _resolve_db_path(
    env_path: Optional[Path] = None, db_path: Optional[Path] = None
) -> Path:
    """Resolve database path with proper precedence.

    1. If --db is explicitly provided, use it directly
    2. Otherwise derive from env-loaded RAVEN_DATA_DIR (defaults to system default)

    Args:
        env_path: Optional path to .env file
        db_path: Optional explicit db path from --db option

    Returns:
        Resolved Path to the database
    """
    # Load config from env to set RAVEN_DATA_DIR for _get_data_dir()
    _load_config(env_path)

    if db_path is not None:
        # Explicit --db option takes precedence
        return db_path

    # Derive from data_dir (respects RAVEN_DATA_DIR from loaded env)
    return _get_data_dir() / "raven.db"


@click.group()
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Raven - Offline-first CLI research system for academic knowledge curation."""
    ctx.ensure_object(dict)


@cli.command()
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
    default="relevance_score:desc",
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
@click.pass_context
def search(
    ctx: click.Context,
    query: str,
    db: Optional[Path],
    env: Optional[Path],
    filter: Optional[str],
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
        # Local database search (original behavior)
        from raven.storage import search_papers

        results = search_papers(db_path, query)

        if not results:
            click.echo("No results found in local database.")
            return

        for paper in results:
            click.echo(f"Title: {paper['title']}")
            click.echo(f"DOI: {paper['doi']}")
            click.echo(f"Type: {paper['type']}")
            click.echo("---")
    else:
        # OpenAlex search
        from raven.ingestion import format_search_result, search_works

        result_data = search_works(
            query=query,
            filter=filter,
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

        for i, work in enumerate(results, 1):
            formatted = format_search_result(work)
            click.echo(f"{i}. {formatted['title']}")
            click.echo(f"   DOI: {formatted['doi'] or 'N/A'}")
            click.echo(f"   Year: {formatted.get('publication_year', 'N/A')}")
            click.echo(f"   Type: {formatted['type']}")
            click.echo(f"   Citations: {formatted.get('cited_by_count', 0)}")
            click.echo(
                f"   Open Access: {'Yes' if formatted.get('open_access') else 'No'}"
            )
            if formatted.get("relevance_score"):
                click.echo(f"   Relevance: {formatted['relevance_score']:.3f}")
            if formatted.get("abstract"):
                abstract_preview = formatted["abstract"][:300]
                if len(formatted["abstract"]) > 300:
                    abstract_preview += "..."
                click.echo(f"   Abstract: {abstract_preview}")
            click.echo("---")

        # Prompt for ingestion if results found
        if results:
            click.echo("To ingest a paper, run:")
            click.echo("  raven ingest <DOI>")
            click.echo("Or use the interactive mode (coming soon).")


@cli.command()
@click.argument("doi")
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
@click.pass_context
def ingest(
    ctx: click.Context, doi: str, db: Optional[Path], env: Optional[Path]
) -> None:
    """Ingest a publication by DOI."""
    from raven.ingestion import ingest_paper

    db_path = _resolve_db_path(env, db)

    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Ingesting DOI: {doi}...")

    result = ingest_paper(db_path, doi)

    if result:
        click.echo(f"Successfully ingested: {result['title']}")
    else:
        click.echo("Failed to ingest publication.", err=True)


@cli.command()
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
@click.pass_context
def init(ctx: click.Context, db: Optional[Path], env: Optional[Path]) -> None:
    """Initialize the database."""
    from raven.storage import init_database

    db_path = _resolve_db_path(env, db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    init_database(db_path)
    click.echo(f"Database initialized at: {db_path}")


def _format_size(size_bytes: float) -> str:
    """Format bytes into human-readable size string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


@cli.group()
def cache() -> None:
    """Manage the model cache."""
    pass


@cache.command()
def status() -> None:
    """Show cache status and size."""
    from raven.embeddings import _get_model_cache_dir

    cache_dir = _get_model_cache_dir()
    cache_size = get_model_cache_size()

    click.echo(f"Cache directory: {cache_dir}")

    if cache_size is None:
        click.echo("Cache size: No cache found")
    else:
        click.echo(f"Cache size: {_format_size(cache_size)}")


@cache.command()
def clean() -> None:
    """Delete the model cache."""
    clean_model_cache()
    click.echo("Cache cleaned successfully")


@cli.command()
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
@click.pass_context
def info(ctx: click.Context, db: Optional[Path], env: Optional[Path]) -> None:
    """Show details about the current Raven configuration."""
    import sqlite3

    db_path = _resolve_db_path(env, db)
    data_dir = _get_data_dir()

    # Get total unique DOIs
    total_papers = 0
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(DISTINCT doi) FROM papers")
                total_papers = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            click.echo(
                "Warning: Database exists but 'papers' table not found.", err=True
            )
            total_papers = 0

    click.echo(f"Version: {_get_version()}")
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Database: {db_path}")
    click.echo(f"Total papers indexed: {total_papers}")


if __name__ == "__main__":
    cli.main(standalone_mode=False)
