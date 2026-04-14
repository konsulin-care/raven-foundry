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


def extract_identifier(ids: dict[str, str] | None) -> str | None:
    """Extract identifier from OpenAlex work IDs using priority: doi > openalex > pmid > mag.

    Args:
        ids: Dictionary of OpenAlex work IDs with keys like 'doi', 'openalex', 'pmid', 'mag'.

    Returns:
        Formatted identifier string (e.g., 'doi:10.5281/zenodo.18201069') or None if no IDs available.
    """
    if ids is None:
        return None

    # Priority 1: DOI
    doi = ids.get("doi")
    if doi:
        # Strip https://doi.org/ and add doi: prefix
        doi_value = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        return f"doi:{doi_value}"

    # Priority 2: OpenAlex
    openalex = ids.get("openalex")
    if openalex:
        # Strip https://openalex.org/ and add openalex: prefix
        openalex_value = openalex.replace("https://openalex.org/", "")
        return f"openalex:{openalex_value}"

    # Priority 3: PMID
    pmid = ids.get("pmid")
    if pmid:
        # Strip URL and add pmid: prefix
        pmid_value = pmid.replace("https://pubmed.ncbi.nlm.nih.gov/", "")
        return f"pmid:{pmid_value}"

    # Priority 4: MAG
    mag = ids.get("mag")
    if mag:
        # Just add mag: prefix
        return f"mag:{mag}"

    # No IDs available
    return None


def _load_vector_extension(conn: sqlite3.Connection) -> None:
    """Load the sqliteai-vector extension.

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
        raise RuntimeError(f"Failed to load sqliteai-vector extension: {e}") from e
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


def _safe_add_column(conn: sqlite3.Connection, col_name: str, col_type: str) -> None:
    """Safely add a column with validation and quoting.

    This helper combines whitelist validation with identifier quoting to
    provide defense-in-depth against SQL injection in DDL statements.

    Args:
        conn: SQLite connection.
        col_name: Column name to add.
        col_type: SQL type (e.g., "TEXT", "INTEGER").

    Raises:
        ValueError: If column name is not in whitelist.
    """
    # Whitelist of valid column names for migration
    valid_column_names = frozenset(
        {
            "authors",
            "abstract",
            "publication_year",
            "venue",
            "openalex_id",
            "identifier",
        }
    )

    # Validate against whitelist
    if col_name not in valid_column_names:
        raise ValueError(f"Invalid column name in migration: {col_name}")

    # Execute with quoted identifier to prevent SQL injection
    conn.execute(f"ALTER TABLE papers ADD COLUMN [{col_name}] {col_type}")


def init_database(db_path: Path) -> None:
    """Initialize the database with schema and vector support.

    Args:
        db_path: Path to the SQLite database file.
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        # Enable and load sqliteai-vector extension
        _load_vector_extension(conn)

        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                openalex_id TEXT UNIQUE,
                identifier TEXT UNIQUE NOT NULL COLLATE NOCASE,
                title TEXT NOT NULL,
                authors TEXT,
                abstract TEXT,
                publication_year INTEGER,
                venue TEXT,
                type TEXT DEFAULT 'article',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migration: Add missing columns for existing databases
        columns_result = conn.execute("PRAGMA table_info('papers')").fetchall()
        existing_columns = {row[1] for row in columns_result}

        columns_to_add = {
            "authors": "TEXT",
            "abstract": "TEXT",
            "publication_year": "INTEGER",
            "venue": "TEXT",
            "openalex_id": "TEXT",
            "identifier": "TEXT",
        }

        # Add missing columns using safe helper
        for col_name, col_type in columns_to_add.items():
            if col_name not in existing_columns:
                _safe_add_column(conn, col_name, col_type)

        # Migration: Add identifier column and migrate from doi
        if "doi" in existing_columns and "identifier" not in existing_columns:
            # Step 1: Add identifier column as nullable first
            _safe_add_column(conn, "identifier", "TEXT")

            # Step 2: Migrate existing doi data to identifier (format: doi:xxxxx)
            conn.execute("""
                UPDATE papers
                SET identifier = 'doi:' || doi
                WHERE doi IS NOT NULL AND doi != ''
            """)

            # Step 3: Create identifier index and drop doi index
            conn.execute("DROP INDEX IF EXISTS idx_papers_doi")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier COLLATE NOCASE)"
            )

            # Step 4: Drop doi column after migration
            conn.execute("ALTER TABLE papers DROP COLUMN doi")

        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_openalex_id ON papers(openalex_id)"
        )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier COLLATE NOCASE)"
        )

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_type ON papers(type)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year)
        """)

        # Create vector embeddings table using sqliteai-vector (sqliteai-vector package)
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
        return row[0] if row else None  # type: ignore[return-value]


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
            return cursor.lastrowid  # type: ignore[return-value]
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
        # Load sqliteai-vector extension
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
        # Load sqliteai-vector extension
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
                p.identifier,
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
