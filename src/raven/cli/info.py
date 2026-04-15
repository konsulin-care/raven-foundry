"""Info command for Raven CLI."""

import sqlite3
from pathlib import Path
from typing import Optional

import click


def _format_size(size_bytes: float) -> str:
    """Format bytes into human-readable size string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


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
    """Resolve database path with proper precedence."""
    from raven.config import _get_data_dir, _load_config

    _load_config(env_path)

    if db_path is not None:
        return db_path

    return _get_data_dir() / "raven.db"


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
def info(db: Optional[Path], env: Optional[Path]) -> None:
    """Show details about the current Raven configuration."""
    from raven.config import _get_data_dir

    db_path = _resolve_db_path(env, db)
    data_dir = _get_data_dir()

    # Get total unique identifiers
    total_papers = 0
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT COUNT(DISTINCT identifier) FROM papers")
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
