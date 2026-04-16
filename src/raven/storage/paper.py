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
    import hashlib

    return "A" + hashlib.md5().hexdigest()[:10].upper()


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
) -> None:
    """Add paper-author relationships to the junction table.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper.
        authors_data: List of author data dicts with keys: id, name, orcid, is_corresponding, order.
    """
    if not authors_data:
        return

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        # Check if normalized tables exist (backward compatibility)
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}

        if "authors" not in table_names or "paper_authors" not in table_names:
            return  # Skip if old database schema

        for author in authors_data:
            # Ensure author exists in authors table
            conn.execute(
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
            conn.execute(
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
        conn.commit()


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


def delete_paper_authors(db_path: Path, paper_id: int) -> None:
    """Delete all author relationships for a paper.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper.
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            "DELETE FROM paper_authors WHERE paper_id = ?",
            (paper_id,),
        )
        conn.commit()


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
            # Use normalized schema
            cursor = conn.execute(
                """
                SELECT
                    p.id,
                    p.identifier,
                    p.title,
                    p.abstract,
                    p.publication_year,
                    p.venue,
                    p.type,
                    GROUP_CONCAT(a.name, ', ') AS authors
                FROM papers p
                LEFT JOIN paper_authors pa ON p.id = pa.paper_id
                LEFT JOIN authors a ON pa.author_id = a.id
                WHERE LOWER(p.title) LIKE LOWER(?) OR LOWER(p.identifier) LIKE LOWER(?)
                GROUP BY p.id
                LIMIT 50
            """,
                (f"%{query}%", f"%{query}%"),
            )
        else:
            # Fallback to legacy authors column
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
    authors_data: list[dict[str, Any]] | None = None,
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
        authors: Comma-separated list of authors (deprecated, use authors_data).
        authors_data: List of author data dicts with keys: id, name, orcid, is_corresponding, order (optional).
        abstract: Paper abstract (optional).
        publication_year: Year of publication (optional).
        venue: Publication venue/journal (optional).
        openalex_id: OpenAlex ID for the paper (optional).

    Returns:
        The ID of the newly inserted paper.

    Raises:
        ValueError: If a paper with the same identifier already exists.
    """
    # Backward compatibility: convert authors string to authors_data
    if authors_data is None and authors:
        import hashlib

        author_names = [n.strip() for n in authors.split(",") if n.strip()]
        authors_data = []
        for idx, name in enumerate(author_names):
            author_id = "A" + hashlib.md5(name.encode()).hexdigest()[:10].upper()
            authors_data.append(
                {
                    "id": author_id,
                    "name": name,
                    "orcid": None,
                    "is_corresponding": 0,
                    "order": idx,
                }
            )

    # Build comma-separated authors string for backward compatibility
    authors_str = None
    if authors_data:
        authors_str = ", ".join(a["name"] for a in authors_data if a.get("name"))
    elif authors:
        authors_str = authors

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        try:
            # Check if authors column exists in papers table (backward compatibility)
            columns = conn.execute("PRAGMA table_info('papers')").fetchall()
            has_authors_column = any(col[1] == "authors" for col in columns)

            # Coerce None to empty string for identifier field (NOT NULL constraint)
            identifier_value = identifier if identifier is not None else ""
            if has_authors_column:
                cursor = conn.execute(
                    """
                    INSERT INTO papers (identifier, title, authors, abstract, publication_year, venue, openalex_id, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        identifier_value,
                        title,
                        authors_str,
                        abstract,
                        publication_year,
                        venue,
                        openalex_id,
                        paper_type,
                    ),
                )
            else:
                cursor = conn.execute(
                    """
                    INSERT INTO papers (identifier, title, abstract, publication_year, venue, openalex_id, type)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        identifier_value,
                        title,
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

            # Add authors to junction table if provided
            if authors_data:
                add_paper_authors(db_path, result, authors_data)

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
    authors_data: list[dict[str, Any]] | None = None,
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
        authors: Comma-separated list of authors (deprecated, use authors_data).
        authors_data: List of author data dicts with keys: id, name, orcid, is_corresponding, order (optional).
        abstract: Paper abstract (optional).
        publication_year: Year of publication (optional).
        venue: Publication venue/journal (optional).
        openalex_id: OpenAlex ID for the paper (optional).
        paper_type: Type of paper (default: 'article').
    """
    # Backward compatibility: convert authors string to authors_data
    if authors_data is None and authors:
        import hashlib

        author_names = [n.strip() for n in authors.split(",") if n.strip()]
        authors_data = []
        for idx, name in enumerate(author_names):
            author_id = "A" + hashlib.md5(name.encode()).hexdigest()[:10].upper()
            authors_data.append(
                {
                    "id": author_id,
                    "name": name,
                    "orcid": None,
                    "is_corresponding": 0,
                    "order": idx,
                }
            )

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            UPDATE papers SET
                title = ?,
                abstract = ?,
                publication_year = ?,
                venue = ?,
                openalex_id = ?,
                type = ?
            WHERE id = ?
            """,
            (
                title,
                abstract,
                publication_year,
                venue,
                openalex_id,
                paper_type,
                paper_id,
            ),
        )
        conn.commit()

    # Update authors if provided
    if authors_data is not None:
        delete_paper_authors(db_path, paper_id)
        add_paper_authors(db_path, paper_id, authors_data)
