"""Database helpers for search operations."""

import contextlib
import sqlite3
from pathlib import Path
from typing import Any


def check_batch_ingested(db_path: Path, results: list[dict[str, Any]]) -> set[str]:
    """Check which identifiers are ingested (single SQL query).

    Args:
        db_path: Path to the SQLite database.
        results: List of search results with 'identifier' field.

    Returns:
        Set of lowercase identifiers that are already ingested.
        Returns empty set if DB or table is missing.
    """
    identifiers = [r["identifier"].lower() for r in results if r.get("identifier")]
    if not identifiers:
        return set()

    if not db_path.exists():
        return set()

    try:
        with contextlib.closing(sqlite3.connect(db_path)) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='papers'"
            )
            if not cursor.fetchone():
                return set()

            placeholders = ",".join(["?"] * len(identifiers))
            cursor = conn.execute(
                f"SELECT LOWER(identifier) FROM papers WHERE LOWER(identifier) IN ({placeholders})",
                identifiers,
            )
            return {row[0] for row in cursor.fetchall()}
    except (sqlite3.OperationalError, OSError):
        return set()


def search_papers_keyword(db_path: Path, query: str) -> list[dict[str, Any]]:
    """Search papers by title or identifier (keyword search).

    Args:
        db_path: Path to the SQLite database.
        query: Search query string.

    Returns:
        List of paper records matching the query.
    """
    from raven.storage.paper import search_papers

    return search_papers(db_path, query)
