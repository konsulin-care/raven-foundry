"""CLI entry point for Raven - offline-first research system."""

from pathlib import Path

import click

# Database path stored in app context
DEFAULT_DB_PATH = Path.home() / ".raven" / "raven.db"


@click.group()
@click.option(
    "--db",
    "-d",
    type=click.Path(path_type=Path),
    default=DEFAULT_DB_PATH,
    help="Path to the database file.",
)
@click.pass_context
def cli(ctx: click.Context, db: Path) -> None:
    """Raven - Offline-first CLI research system for academic knowledge curation."""
    ctx.ensure_object(dict)
    ctx.obj["DB_PATH"] = db


@cli.command()
@click.argument("query")
@click.pass_context
def search(ctx: click.Context, query: str) -> None:
    """Search publications by query string."""
    from raven.storage import search_papers

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
    from raven.ingestion import ingest_paper

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


if __name__ == "__main__":
    cli()
