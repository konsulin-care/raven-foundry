"""CLI entry point for Raven - offline-first research system."""

from pathlib import Path
from typing import Optional

import click

from raven.config import _get_data_dir, _load_config


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
@click.pass_context
def search(
    ctx: click.Context, query: str, db: Optional[Path], env: Optional[Path]
) -> None:
    """Search publications by query string."""
    from raven.storage import search_papers

    db_path = _resolve_db_path(env, db)

    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    results = search_papers(db_path, query)

    if not results:
        click.echo("No results found.")
        return

    for paper in results:
        click.echo(f"Title: {paper['title']}")
        click.echo(f"DOI: {paper['doi']}")
        click.echo(f"Type: {paper['type']}")
        click.echo("---")


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
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT COUNT(DISTINCT doi) FROM papers")
            total_papers = cursor.fetchone()[0]

    click.echo(f"Version: {_get_version()}")
    click.echo(f"Data directory: {data_dir}")
    click.echo(f"Database: {db_path}")
    click.echo(f"Total papers indexed: {total_papers}")


if __name__ == "__main__":
    cli()
