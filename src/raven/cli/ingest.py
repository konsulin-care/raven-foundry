"""Ingest command for Raven CLI."""

from pathlib import Path
from typing import Any, Optional

import click

from raven.ingestion import ingest_paper
from raven.ingestion.bibtex import filter_valid_entries, parse_bibtex_file
from raven.paths import get_data_dir, load_config


def _resolve_db_path(
    env_path: Optional[Path] = None, db_path: Optional[Path] = None
) -> Path:
    """Resolve database path with proper precedence."""
    load_config(env_path)

    if db_path is not None:
        return db_path

    return get_data_dir() / "raven.db"


@click.command()
@click.argument("identifier", required=False)
@click.option(
    "--bib",
    "-b",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="Path to BibTeX file for batch ingestion",
)
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
def ingest(
    identifier: Optional[str],
    bib: Optional[Path],
    db: Optional[Path],
    env: Optional[Path],
) -> None:
    """Ingest a publication by identifier (DOI, OpenAlex ID, PMID, MAG, PMCID).

    Examples:
        raven ingest doi:10.5281/zenodo.18201069
        raven ingest --bib references.bib
    """
    db_path = _resolve_db_path(env, db)

    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # BibTeX batch ingestion
    if bib:
        filename = bib.name

        # Step 1: Parse bib file
        click.echo(f"Parsing {filename} into memory")
        entries = parse_bibtex_file(bib)

        # Step 2: Filter valid entries
        valid_entries, _ = filter_valid_entries(entries)
        total_valid = len(valid_entries)
        total_entries = len(entries)

        click.echo(
            f"Parsed {total_entries} entries, {total_valid} has a valid identifier"
        )

        if not valid_entries:
            click.echo("No valid entries to ingest.")
            return

        # Step 3: Ingest with progress bar
        bar: Any  # click.progressbar is a context manager
        with click.progressbar(
            length=total_valid,
            label="Ingesting",
            show_eta=False,
            show_percent=True,
            show_pos=True,
            item_show_func=lambda e: e["_identifier"] if e else "",
        ) as bar:
            for i, entry in enumerate(valid_entries, 1):
                identifier = entry["_identifier"]
                if identifier is None:
                    raise ValueError("Entry missing required identifier")
                ingest_paper(db_path, identifier)
                bar.update(1)

        click.echo(f"Successfully ingested {total_valid} publications.")
        return

    # Single identifier ingestion
    if not identifier:
        raise click.UsageError("Either provide an identifier or use --bib option")

    click.echo(f"Ingesting: {identifier}...")

    result = ingest_paper(db_path, identifier)

    if result:
        click.echo(f"Successfully ingested: {result['title']}")
    else:
        click.echo("Failed to ingest publication.", err=True)
