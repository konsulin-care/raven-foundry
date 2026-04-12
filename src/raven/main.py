"""CLI entry point for Raven - offline-first research system."""

from pathlib import Path

import click

from raven.config import _get_data_dir

# Database path stored in app context
DEFAULT_DB_PATH = _get_data_dir() / "raven.db"


def _get_version() -> str:
    """Get version from package metadata, default to dev if not installed."""
    try:
        from importlib.metadata import version

        return version("raven-foundry")
    except Exception:
        return "dev"


@click.group()
@click.option(
    "--db",
    "-d",
    type=click.Path(path_type=Path),
    default=DEFAULT_DB_PATH,
    help="Path to the database file.",
)
@click.option(
    "--env",
    "-e",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="Path to .env file (default: cwd/.env → RAVEN_DATA_DIR/.env)",
)
@click.pass_context
def cli(ctx: click.Context, db: Path, env: Path) -> None:
    """Raven - Offline-first CLI research system for academic knowledge curation."""
    ctx.ensure_object(dict)
    ctx.obj["DB_PATH"] = db
    ctx.obj["ENV_PATH"] = env


@cli.command()
@click.argument("query")
@click.pass_context
def search(ctx: click.Context, query: str) -> None:
    """Search publications by query string."""
    from raven.config import _load_config
    from raven.storage import search_papers

    env_path = ctx.obj.get("ENV_PATH")
    _load_config(env_path)

    db_path = ctx.obj["DB_PATH"]
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
@click.pass_context
def ingest(ctx: click.Context, doi: str) -> None:
    """Ingest a publication by DOI."""
    from raven.config import _load_config
    from raven.ingestion import ingest_paper

    env_path = ctx.obj.get("ENV_PATH")
    _load_config(env_path)

    db_path = ctx.obj["DB_PATH"]
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Ingesting DOI: {doi}...")

    result = ingest_paper(db_path, doi)

    if result:
        click.echo(f"Successfully ingested: {result['title']}")
    else:
        click.echo("Failed to ingest publication.", err=True)


@cli.command()
@click.pass_context
def init(ctx: click.Context) -> None:
    """Initialize the database."""
    from raven.storage import init_database

    db_path = ctx.obj["DB_PATH"]
    db_path.parent.mkdir(parents=True, exist_ok=True)

    init_database(db_path)
    click.echo(f"Database initialized at: {db_path}")


@cli.command()
def info() -> None:
    """Show details about the current Raven configuration."""
    import sqlite3

    data_dir = _get_data_dir()
    db_path = data_dir / "raven.db"

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
