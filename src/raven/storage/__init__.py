"""Storage module - SQLite + vector storage for Raven."""

import importlib.resources
import sqlite3
import struct
from pathlib import Path
from typing import Any


def _load_vector_extension(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vector extension.

    Args:
        conn: SQLite connection to load the extension into.
    """
    ext_path = importlib.resources.files("sqlite_vector.binaries") / "vector"
    conn.enable_load_extension(True)
    try:
        conn.load_extension(str(ext_path))
    finally:
        conn.enable_load_extension(False)


# Schema based on AGENTS.md:
# - 384-dim embeddings
# - Metadata (DOI, title, type, timestamps)
# - Enforce DOI uniqueness
# - Use WAL mode for durability
# - Maintain indexes on DOI, type, title


def serialize_f32(vector: list[float]) -> bytes:
    """Serialize float list to compact binary format for sqlite-vec.

    Args:
        vector: List of floats representing the embedding vector.

    Returns:
        Packed binary representation of the vector.
    """
    return struct.pack("%sf" % len(vector), *vector)


def init_database(db_path: Path) -> None:
    """Initialize the database with schema and vector support.

    Args:
        db_path: Path to the SQLite database file.
    """
    with sqlite3.connect(db_path) as conn:
        # Enable and load sqlite-vector extension
        _load_vector_extension(conn)

        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                openalex_id TEXT UNIQUE,
                doi TEXT UNIQUE NOT NULL COLLATE NOCASE,
                title TEXT NOT NULL,
                authors TEXT,
                abstract TEXT,
                publication_year INTEGER,
                venue TEXT,
                type TEXT DEFAULT 'article',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_type ON papers(type)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year)
        """)

        # Create vector embeddings table using sqlite-vector (optional - may fail if extension not available)
        try:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
                    paper_id INTEGER PRIMARY KEY,
                    embedding float[384]
                )
            """)
        except sqlite3.OperationalError:
            # Extension not available - vector search will not work
            pass

        conn.commit()


def search_papers(db_path: Path, query: str) -> list[dict[str, Any]]:
    """Search papers by title or DOI (case-insensitive).

    Args:
        db_path: Path to the SQLite database file.
        query: Search query string.

    Returns:
        List of paper records matching the query.
    """
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT id, doi, title, authors, abstract, publication_year, venue, type
            FROM papers
            WHERE LOWER(title) LIKE LOWER(?) OR LOWER(doi) LIKE LOWER(?)
            LIMIT 50
        """,
            (f"%{query}%", f"%{query}%"),
        )

        results = [dict(row) for row in cursor.fetchall()]

    return results


def get_paper_id_by_doi(db_path: Path, doi: str | None) -> int | None:
    """Get paper ID by DOI.

    Args:
        db_path: Path to the SQLite database file.
        doi: DOI of the paper to look up.

    Returns:
        The paper ID if found, None if not found.
    """
    if doi is None:
        return None

    with sqlite3.connect(db_path) as conn:
        cursor = conn.execute(
            "SELECT id FROM papers WHERE LOWER(doi) = LOWER(?)",
            (doi,),
        )
        row = cursor.fetchone()
        return row[0] if row else None  # type: ignore[return-value]


def add_paper(
    db_path: Path,
    doi: str | None,
    title: str,
    authors: str | None = None,
    abstract: str | None = None,
    publication_year: int | None = None,
    venue: str | None = None,
    openalex_id: str | None = None,
    paper_type: str = "article",
) -> int:
    """Add a paper to the database.

    Args:
        db_path: Path to the SQLite database file.
        doi: DOI of the paper (optional).
        title: Title of the paper.
        authors: Comma-separated list of authors (optional).
        abstract: Paper abstract (optional).
        publication_year: Year of publication (optional).
        venue: Publication venue/journal (optional).
        openalex_id: OpenAlex ID for the paper (optional).
        paper_type: Type of paper (default: 'article').

    Returns:
        The ID of the newly inserted paper.

    Raises:
        ValueError: If a paper with the same DOI already exists.
    """
    with sqlite3.connect(db_path) as conn:
        try:
            cursor = conn.execute(
                """
                INSERT INTO papers (doi, title, authors, abstract, publication_year, venue, openalex_id, type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    doi,
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
            return cursor.lastrowid  # type: ignore[return-value]
        except sqlite3.IntegrityError as e:
            error_msg = str(e)
            # Check if it's specifically a DOI uniqueness constraint violation
            if "UNIQUE constraint failed" in error_msg and "doi" in error_msg.lower():
                raise ValueError(f"Paper with DOI {doi} already exists")
            # Re-raise unrelated integrity errors
            raise


def add_embedding(db_path: Path, paper_id: int, embedding: list[float]) -> None:
    """Add vector embedding for a paper.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper to associate the embedding with.
        embedding: 384-dimensional embedding vector.

    Raises:
        ValueError: If the embedding vector length doesn't match expected dimension.
    """
    expected_dim = 384
    if len(embedding) != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch: expected {expected_dim}, got {len(embedding)}"
        )

    with sqlite3.connect(db_path) as conn:
        # Load sqlite-vector extension
        _load_vector_extension(conn)

        # Insert embedding into vector table
        serialized = serialize_f32(embedding)
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (paper_id, embedding) VALUES (?, ?)",
            (paper_id, serialized),
        )
        conn.commit()


def search_by_embedding(
    db_path: Path, query_embedding: list[float], top_k: int = 10
) -> list[dict[str, Any]]:
    """Search papers by vector similarity (KNN).

    Args:
        db_path: Path to the SQLite database file.
        query_embedding: 384-dimensional query embedding vector.
        top_k: Number of nearest neighbors to return (default: 10).

    Returns:
        List of paper records with distance scores, sorted by similarity.

    Raises:
        ValueError: If the query embedding dimension doesn't match expected dimension.
    """
    expected_dim = 384
    if len(query_embedding) != expected_dim:
        raise ValueError(
            f"Query embedding dimension mismatch: expected {expected_dim}, got {len(query_embedding)}"
        )

    with sqlite3.connect(db_path) as conn:
        # Load sqlite-vector extension
        _load_vector_extension(conn)

        # Serialize query and run KNN search
        serialized = serialize_f32(query_embedding)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT
                p.id,
                p.doi,
                p.title,
                p.authors,
                p.abstract,
                p.publication_year,
                p.venue,
                p.type,
                e.distance
            FROM embeddings e
            JOIN papers p ON e.paper_id = p.id
            WHERE e.embedding MATCH ?
            ORDER BY e.distance
            LIMIT ?
            """,
            (serialized, top_k),
        )

        results = [dict(row) for row in cursor.fetchall()]

    return results
