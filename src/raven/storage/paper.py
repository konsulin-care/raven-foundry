"""Paper CRUD operations for Raven storage.

Rules:
- Enforce DOI uniqueness
- Use normalized author schema (authors + paper_authors tables)
"""

import contextlib
import logging
import sqlite3
from pathlib import Path
from typing import Any

from raven.storage.paper_authors import (
    add_paper_authors,
    convert_authors_to_data,
    delete_paper_authors,
)
from raven.storage.paper_queries import (
    get_paper_id_by_doi,
    get_paper_id_by_identifier,
    search_papers,
)

logger = logging.getLogger(__name__)

__all__ = [
    "add_paper",
    "update_paper",
    "search_papers",
    "get_paper_id_by_identifier",
    "get_paper_id_by_doi",
]


def add_paper(
    db_path: Path,
    identifier: str | None,
    title: str,
    paper_type: str = "article",
    authors: str | None = None,
    authors_data: list[dict[str, Any]] | None = None,
    abstract: str | None = None,
    year: int | None = None,
    source: str | None = None,
) -> int:
    """Add a paper to the database.

    Args:
        db_path: Path to the SQLite database file.
        identifier: Identifier of the paper (e.g., 'doi:10.1234/abc', 'openalex:W12345').
        title: Title of the paper.
        paper_type: Type of paper (default: 'article').
        authors: Comma-separated list of authors (deprecated, use authors_data).
        authors_data: List of author data dicts with keys: id, name, orcid, is_corresponding, order (optional).
        abstract: Paper abstract (optional).
        year: Year of publication (optional).
        source: Publication source/journal (optional).

    Returns:
        The ID of the newly inserted paper.

    Raises:
        ValueError: If a paper with the same identifier already exists.
    """
    # Backward compatibility: convert authors string to authors_data
    if authors_data is None and authors:
        authors_data = convert_authors_to_data(authors)

    # Build comma-separated authors string for legacy column (if it exists)
    authors_str = None
    if authors_data:
        authors_str = ", ".join(a["name"] for a in authors_data if a.get("name"))
    elif authors:
        authors_str = authors

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        try:
            # Check if legacy authors column exists
            columns = conn.execute("PRAGMA table_info('papers')").fetchall()
            has_authors_col = any(col[1] == "authors" for col in columns)

            # Coerce None to empty string for identifier field (NOT NULL constraint)
            identifier_value = identifier if identifier is not None else ""

            if has_authors_col:
                cursor = conn.execute(
                    """INSERT INTO papers (identifier, title, authors, abstract,
                       year, source, type)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        identifier_value,
                        title,
                        authors_str,
                        abstract,
                        year,
                        source,
                        paper_type,
                    ),
                )
            else:
                cursor = conn.execute(
                    """INSERT INTO papers (identifier, title, abstract,
                       year, source, type)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        identifier_value,
                        title,
                        abstract,
                        year,
                        source,
                        paper_type,
                    ),
                )
            conn.commit()
            result = cursor.lastrowid
            if result is None:
                raise RuntimeError("Failed to insert paper: no rowid returned")

            # Add authors to junction table if provided
            if authors_data:
                add_paper_authors(db_path, result, authors_data)

            return result
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            if (
                "UNIQUE constraint failed" in error_msg
                and "identifier" in error_msg.lower()
            ):
                raise ValueError(
                    f"Paper with identifier {identifier} already exists"
                ) from e
            raise


def update_paper(
    db_path: Path,
    paper_id: int,
    title: str,
    authors: str | None = None,
    authors_data: list[dict[str, Any]] | None = None,
    abstract: str | None = None,
    year: int | None = None,
    source: str | None = None,
    paper_type: str = "article",
) -> None:
    """Update an existing paper's metadata."""
    # Backward compatibility: convert authors string to authors_data
    if authors_data is None and authors:
        authors_data = convert_authors_to_data(authors)

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """UPDATE papers SET title=?, abstract=?, year=?,
               source=?, type=? WHERE id=?""",
            (
                title,
                abstract,
                year,
                source,
                paper_type,
                paper_id,
            ),
        )
        conn.commit()

    # Update authors if provided
    if authors_data is not None:
        delete_paper_authors(db_path, paper_id)
        add_paper_authors(db_path, paper_id, authors_data)
