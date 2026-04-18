"""Paper author operations for Raven storage.

Handles normalized author schema with authors + paper_authors tables.
"""

import contextlib
import hashlib
import logging
import sqlite3
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


def _get_author_id_from_orcid(orcid: str | None) -> str:
    """Generate author ID from ORCID or create a new one.

    Args:
        orcid: ORCID identifier (with or without https://orcid.org/).

    Returns:
        OpenAlex author ID (e.g., "A5048491430").
    """
    if orcid:
        # ORCID is already linked to an OpenAlex author ID
        # We store the orcid and will resolve to author ID via lookup
        return orcid.replace("https://orcid.org/", "").replace("0000-", "A0000-")
    return "A" + hashlib.sha256().hexdigest()[:10].upper()


def add_author(
    db_path: Path, author_id: str, name: str, orcid: str | None = None
) -> None:
    """Add or update an author in the authors table.

    Args:
        db_path: Path to the SQLite database file.
        author_id: OpenAlex author ID.
        name: Author's display name.
        orcid: ORCID identifier (optional).
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO authors (id, orcid, name)
            VALUES (?, ?, ?)
            """,
            (author_id, orcid, name),
        )
        conn.commit()


def add_paper_authors(
    db_path: Path,
    paper_id: int,
    authors_data: list[dict[str, Any]] | None,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Add paper-author relationships to the junction table.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper.
        authors_data: List of author data dicts with keys: id, name, orcid, is_corresponding, order.
        conn: SQLite connection object. If provided, uses this connection (caller controls commit).
                If None, creates a new connection using db_path and commits internally.
    """
    if not authors_data:
        return

    own_connection = conn is None
    if own_connection:
        conn = sqlite3.connect(db_path)

    connection = cast(sqlite3.Connection, conn)

    try:
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}

        if "authors" not in table_names or "paper_authors" not in table_names:
            return  # Skip if old database schema

        for author in authors_data:
            # Ensure author exists in authors table
            connection.execute(
                """
                INSERT OR IGNORE INTO authors (id, orcid, name)
                VALUES (?, ?, ?)
                """,
                (
                    author.get("id"),
                    author.get("orcid"),
                    author.get("name"),
                ),
            )

            # Add junction entry
            connection.execute(
                """
                INSERT OR REPLACE INTO paper_authors
                    (paper_id, author_id, author_order, is_corresponding)
                VALUES (?, ?, ?, ?)
                """,
                (
                    paper_id,
                    author.get("id"),
                    author.get("order", 0),
                    author.get("is_corresponding", 0),
                ),
            )
        # Commit only if we created the connection; caller controls commit when using external conn
        if own_connection:
            connection.commit()
    finally:
        if own_connection:
            connection.close()


def get_paper_authors(db_path: Path, paper_id: int) -> list[dict[str, Any]]:
    """Get authors for a paper from the junction table.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper.

    Returns:
        List of author data dicts.
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            """
            SELECT a.id, a.orcid, a.name, pa.author_order, pa.is_corresponding
            FROM paper_authors pa
            JOIN authors a ON pa.author_id = a.id
            WHERE pa.paper_id = ?
            ORDER BY pa.author_order
            """,
            (paper_id,),
        )
        results = [dict(row) for row in cursor.fetchall()]
    return results


def delete_paper_authors(
    db_path: Path,
    paper_id: int,
    conn: sqlite3.Connection | None = None,
) -> None:
    """Delete all author relationships for a paper.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper.
        conn: SQLite connection object. If provided, uses this connection (caller controls commit).
                If None, creates a new connection using db_path and commits internally.
    """
    own_connection = conn is None
    if own_connection:
        conn = sqlite3.connect(db_path)

    connection = cast(sqlite3.Connection, conn)

    try:
        connection.execute(
            "DELETE FROM paper_authors WHERE paper_id = ?",
            (paper_id,),
        )
        if own_connection:
            connection.commit()
    finally:
        if own_connection:
            connection.close()


def convert_authors_to_data(
    authors: str | None,
) -> list[dict[str, Any]] | None:
    """Convert comma-separated authors string to structured data.

    Args:
        authors: Comma-separated author names string.

    Returns:
        List of author dicts with id, name, orcid, is_corresponding, order.
    """
    if not authors:
        return None

    author_names = [n.strip() for n in authors.split(",") if n.strip()]
    authors_data = []
    for idx, name in enumerate(author_names):
        author_id = "A" + hashlib.sha256(name.encode()).hexdigest()[:10].upper()
        authors_data.append(
            {
                "id": author_id,
                "name": name,
                "orcid": None,
                "is_corresponding": 0,
                "order": idx,
            }
        )
    return authors_data
