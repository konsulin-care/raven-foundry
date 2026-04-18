"""Paper query operations for Raven storage.

Lookup and search functions for papers.
"""

import contextlib
import sqlite3
from pathlib import Path
from typing import Any


def search_papers(db_path: Path, query: str) -> list[dict[str, Any]]:
    """Search papers by title or identifier (case-insensitive).

    Args:
        db_path: Path to the SQLite database file.
        query: Search query string.

    Returns:
        List of paper records matching the query.
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row

        # Check if normalized author tables exist
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}

        if "authors" in table_names and "paper_authors" in table_names:
            cursor = conn.execute(
                """SELECT p.id, p.identifier, p.title, p.abstract,
                   p.year, p.source, p.type, p.ingested_at,
                   GROUP_CONCAT(a.name, ', ') AS authors
                   FROM papers p
                   LEFT JOIN paper_authors pa ON p.id = pa.paper_id
                   LEFT JOIN authors a ON pa.author_id = a.id
                   WHERE LOWER(p.title) LIKE LOWER(?) OR LOWER(p.identifier) LIKE LOWER(?)
                   GROUP BY p.id LIMIT 50""",
                (f"%{query}%", f"%{query}%"),
            )
        else:
            cursor = conn.execute(
                """SELECT id, identifier, title, authors, abstract,
                   year, source, type, ingested_at
                   FROM papers
                   WHERE LOWER(title) LIKE LOWER(?) OR LOWER(identifier) LIKE LOWER(?)
                   LIMIT 50""",
                (f"%{query}%", f"%{query}%"),
            )

        return [dict(row) for row in cursor.fetchall()]


def get_paper_id_by_identifier(db_path: Path, identifier: str | None) -> int | None:
    """Get paper ID by identifier.

    Args:
        db_path: Path to the SQLite database file.
        identifier: Identifier of the paper to look up (e.g., 'doi:10.1234/abc').

    Returns:
        The paper ID if found, None if not found.
    """
    if identifier is None:
        return None

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.execute(
            "SELECT id FROM papers WHERE LOWER(identifier) = LOWER(?)",
            (identifier,),
        )
        row = cursor.fetchone()
        return row[0] if row else None


def get_paper_id_by_doi(db_path: Path, doi: str | None) -> int | None:
    """Get paper ID by DOI (backward compatibility alias).

    Args:
        db_path: Path to the SQLite database file.
        doi: DOI of the paper to look up (e.g., '10.1234/abc' or 'doi:10.1234/abc').

    Returns:
        The paper ID if found, None if not found.
    """
    if doi is None:
        return None

    # Strip doi: prefix if present to get actual identifier
    identifier = doi.replace("doi:", "") if doi.startswith("doi:") else doi
    return get_paper_id_by_identifier(db_path, f"doi:{identifier}")
