"""CLI entry point for Raven - offline-first research system."""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from raven.cli.lazy_group import LazyGroup
from raven.config import _get_data_dir, _load_config

# Lazy-loaded subcommands map
# Format: "command_name": "module.path:command_object_name"
_LAZY_SUBCOMMANDS = {
    "search": "raven.cli.search:search",
    "ingest": "raven.cli.ingest:ingest",
    "init": "raven.cli.init:init",
    "info": "raven.cli.info:info",
    "cache": "raven.cli.cache:cache",
}

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
    env_path: Optional[click.Path] = None, db_path: Optional[click.Path] = None
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
    # click.Path converts to str via __fspath__
    env_path_obj: Optional[Path] = Path(str(env_path)) if env_path else None
    _load_config(env_path_obj)

    if db_path is not None:
        # Explicit --db option takes precedence
        return Path(str(db_path))

    # Derive from data_dir (respects RAVEN_DATA_DIR from loaded env)
    return _get_data_dir() / "raven.db"


@click.group(
    cls=LazyGroup,
    lazy_subcommands=_LAZY_SUBCOMMANDS,
)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Raven - Offline-first CLI research system for academic knowledge curation."""
    ctx.ensure_object(dict)


if __name__ == "__main__":
    cli.main(standalone_mode=False)
