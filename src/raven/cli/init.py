"""Init command for Raven CLI."""

from pathlib import Path
from typing import Optional

import click

from raven.paths import get_data_dir, load_config
from raven.storage import init_database


def _resolve_db_path(
    env_path: Optional[Path] = None, db_path: Optional[Path] = None
) -> Path:
    """Resolve database path with proper precedence."""
    load_config(env_path)

    if db_path is not None:
        return db_path

    return get_data_dir() / "raven.db"


@click.command()
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
def init(db: Optional[Path], env: Optional[Path]) -> None:
    """Initialize the database."""
    db_path = _resolve_db_path(env, db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    init_database(db_path)
    click.echo(f"Database initialized at: {db_path}")
