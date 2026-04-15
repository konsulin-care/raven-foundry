"""Cache commands for Raven CLI."""

import click

from raven.embeddings import (
    _get_model_cache_dir,
    clean_model_cache,
    get_model_cache_size,
)


def _format_size(size_bytes: float) -> str:
    """Format bytes into human-readable size string."""
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


@click.group()
def cache() -> None:
    """Manage the model cache."""
    pass


@cache.command()
def status() -> None:
    """Show cache status and size."""
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
