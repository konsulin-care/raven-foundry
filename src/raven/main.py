"""CLI entry point for Raven - offline-first research system."""

import logging
import sys

import click

from raven.cli.lazy_group import LazyGroup

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
