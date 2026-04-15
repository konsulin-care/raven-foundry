"""Paper CRUD operations for Raven storage.

Rules:
- Enforce DOI uniqueness
"""

import contextlib
import logging
import sqlite3
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


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

        cursor = conn.execute(
            """
            SELECT id, identifier, title, authors, abstract, publication_year, venue, type
            FROM papers
            WHERE LOWER(title) LIKE LOWER(?) OR LOWER(identifier) LIKE LOWER(?)
            LIMIT 50
        """,
            (f"%{query}%", f"%{query}%"),
        )

        results = [dict(row) for row in cursor.fetchall()]

    return results


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


def add_paper(
    db_path: Path,
    identifier: str | None,
    title: str,
    paper_type: str = "article",
    authors: str | None = None,
    abstract: str | None = None,
    publication_year: int | None = None,
    venue: str | None = None,
    openalex_id: str | None = None,
) -> int:
    """Add a paper to the database.

    Args:
        db_path: Path to the SQLite database file.
        identifier: Identifier of the paper (e.g., 'doi:10.1234/abc', 'openalex:W12345').
        title: Title of the paper.
        paper_type: Type of paper (default: 'article').
        authors: Comma-separated list of authors (optional).
        abstract: Paper abstract (optional).
        publication_year: Year of publication (optional).
        venue: Publication venue/journal (optional).
        openalex_id: OpenAlex ID for the paper (optional).

    Returns:
        The ID of the newly inserted paper.

    Raises:
        ValueError: If a paper with the same identifier already exists.
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        try:
            # Coerce None to empty string for identifier field (NOT NULL constraint)
            identifier_value = identifier if identifier is not None else ""
            cursor = conn.execute(
                """
                INSERT INTO papers (identifier, title, authors, abstract, publication_year, venue, openalex_id, type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    identifier_value,
                    title,
                    authors,
                    abstract,
                    publication_year,
                    venue,
                    openalex_id,
                    paper_type,
                ),
            )
            conn.commit()
            result = cursor.lastrowid
            assert result is not None, "Insert should return last rowid"
            return result
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            # Check if it's specifically an identifier uniqueness constraint violation
            if (
                "UNIQUE constraint failed" in error_msg
                and "identifier" in error_msg.lower()
            ):
                raise ValueError(f"Paper with identifier {identifier} already exists")
            # Re-raise unrelated integrity errors
            raise


def update_paper(
    db_path: Path,
    paper_id: int,
    title: str,
    authors: str | None = None,
    abstract: str | None = None,
    publication_year: int | None = None,
    venue: str | None = None,
    openalex_id: str | None = None,
    paper_type: str = "article",
) -> None:
    """Update an existing paper's metadata.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper to update.
        title: Title of the paper.
        authors: Comma-separated list of authors (optional).
        abstract: Paper abstract (optional).
        publication_year: Year of publication (optional).
        venue: Publication venue/journal (optional).
        openalex_id: OpenAlex ID for the paper (optional).
        paper_type: Type of paper (default: 'article').
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            UPDATE papers SET
                title = ?,
                authors = ?,
                abstract = ?,
                publication_year = ?,
                venue = ?,
                openalex_id = ?,
                type = ?
            WHERE id = ?
            """,
            (
                title,
                authors,
                abstract,
                publication_year,
                venue,
                openalex_id,
                paper_type,
                paper_id,
            ),
        )
        conn.commit()
