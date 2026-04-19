"""Paper author operations for Raven storage.

Handles normalized author schema with authors + paper_authors tables.
"""

import contextlib
import logging
import sqlite3
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)


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
            author_id = author.get("id")
            author_name = author.get("name")
            author_orcid = author.get("orcid")

            existing = connection.execute(
                "SELECT name, orcid FROM authors WHERE id = ?", (author_id,)
            ).fetchone()
            if existing and existing[0] != author_name:
                logger.error(
                    "Author ID collision: %s maps to '%s' but trying to insert '%s'. "
                    "Manual intervention required.",
                    author_id,
                    existing[0],
                    author_name,
                )
                raise RuntimeError(
                    f"Author ID collision: {author_id} maps to '{existing[0]}' "
                    f"but trying to insert '{author_name}'. Manual intervention required."
                )

            author_exists = bool(existing)

            if author_orcid and not author_exists:
                orcid_existing = connection.execute(
                    "SELECT id FROM authors WHERE orcid = ?", (author_orcid,)
                ).fetchone()
                if orcid_existing:
                    logger.error(
                        "ORCID collision: %s already maps to author '%s' but trying to add author '%s'. "
                        "Manual intervention required to merge or reassign.",
                        author_orcid,
                        orcid_existing[0],
                        author_id,
                    )
                    raise RuntimeError(
                        f"ORCID collision: '{author_orcid}' already belongs to author "
                        f"'{orcid_existing[0]}' but trying to insert '{author_id}'. "
                        "Manual intervention required."
                    )

            if not author_exists:
                connection.execute(
                    """
                    INSERT INTO authors (id, orcid, name)
                    VALUES (?, ?, ?)
                    """,
                    (author_id, author_orcid, author_name),
                )

            connection.execute(
                """
                INSERT OR REPLACE INTO paper_authors
                    (paper_id, author_id, author_order, is_corresponding)
                VALUES (?, ?, ?, ?)
                """,
                (
                    paper_id,
                    author_id,
                    author.get("order", 0),
                    author.get("is_corresponding", 0),
                ),
            )
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
