"""Storage module - SQLite + vector storage for Raven."""

import contextlib
import importlib.resources
import json
import logging
import sqlite3
import struct
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_vector_extension(conn: sqlite3.Connection) -> None:
    """Load the sqlite-vector extension.

    Args:
        conn: SQLite connection to load the extension into.

    Raises:
        RuntimeError: If the vector extension cannot be loaded.
    """
    ext_path = importlib.resources.files("sqlite_vector.binaries") / "vector"
    conn.enable_load_extension(True)
    try:
        conn.load_extension(str(ext_path))
    except Exception as e:
        raise RuntimeError(f"Failed to load sqlite-vector extension: {e}") from e
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
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
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

        # Create vector embeddings table using sqlite-vector (sqliteai-vector package)
        # Uses regular table with BLOB column + vector_init()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.execute("""
                SELECT vector_init('embeddings', 'embedding',
                                   'type=FLOAT32,dimension=384,distance=COSINE')
            """)
        except sqlite3.OperationalError as e:
            # Extension not available - log error and continue
            logger.warning("Failed to create embeddings table: %s", e)

        conn.commit()


def search_papers(db_path: Path, query: str) -> list[dict[str, Any]]:
    """Search papers by title or DOI (case-insensitive).

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

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.execute(
            "SELECT id FROM papers WHERE LOWER(doi) = LOWER(?)",
            (doi,),
        )
        row = cursor.fetchone()
        return row[0] if row else None  # type: ignore[return-value]


def get_embedding_exists(db_path: Path, paper_id: int) -> bool:
    """Check if embedding exists for a paper.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper to check.

    Returns:
        True if embedding exists, False otherwise.
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM embeddings WHERE paper_id = ?",
            (paper_id,),
        )
        return cursor.fetchone() is not None


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
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
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

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        # Load sqlite-vector extension
        _load_vector_extension(conn)

        # Initialize vector column (required for each new connection)
        conn.execute(
            "SELECT vector_init('embeddings', 'embedding', "
            "'type=FLOAT32,dimension=384,distance=COSINE')"
        )

        # Insert embedding using vector_as_f32 for proper formatting
        embedding_json = json.dumps(embedding)
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (paper_id, embedding) VALUES (?, vector_as_f32(?))",
            (paper_id, embedding_json),
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

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        # Load sqlite-vector extension
        _load_vector_extension(conn)

        # Initialize vector column (required for each new connection)
        conn.execute(
            "SELECT vector_init('embeddings', 'embedding', "
            "'type=FLOAT32,dimension=384,distance=COSINE')"
        )

        # Serialize query and run KNN search using vector_full_scan
        query_json = json.dumps(query_embedding)
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
                v.distance
            FROM embeddings e
            JOIN papers p ON e.paper_id = p.id
            JOIN vector_full_scan('embeddings', 'embedding', vector_as_f32(?), ?) AS v
            ON e.paper_id = v.rowid
            ORDER BY v.distance
            """,
            (query_json, top_k),
        )

        results = [dict(row) for row in cursor.fetchall()]

    return results
