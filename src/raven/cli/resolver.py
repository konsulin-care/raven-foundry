"""Shared CLI utilities for path resolution."""

from pathlib import Path
from typing import Optional

from raven.paths import get_data_dir, load_config


def resolve_db_path(
    env_path: Optional[Path] = None, db_path: Optional[Path] = None
) -> Path:
    """Resolve database path with proper precedence.

    Args:
        env_path: Optional path to .env file
        db_path: Optional explicit db path

    Returns:
        Resolved Path to the database
    """
    load_config(env_path)
    if db_path is not None:
        return db_path
    return get_data_dir() / "raven.db"
