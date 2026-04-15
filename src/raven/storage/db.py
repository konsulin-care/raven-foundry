"""Database initialization and schema management for Raven storage.

Rules:
- Enforce DOI uniqueness
- Use WAL mode for durability
- Maintain indexes on DOI, type, title
"""

import contextlib
import importlib.resources
import logging
import sqlite3
import struct
from pathlib import Path

logger = logging.getLogger(__name__)


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
            "type",
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
        # CRITICAL: Capture original columns BEFORE any modifications
        columns_result = conn.execute("PRAGMA table_info('papers')").fetchall()
        original_columns = {row[1] for row in columns_result}

        columns_to_add = {
            "authors": "TEXT",
            "abstract": "TEXT",
            "publication_year": "INTEGER",
            "venue": "TEXT",
            "openalex_id": "TEXT",
            "identifier": "TEXT",
            "type": "TEXT",
        }

        # Add missing columns (check against ORIGINAL state)
        for col_name, col_type in columns_to_add.items():
            if col_name not in original_columns:
                _safe_add_column(conn, col_name, col_type)

        # Migration: Migrate doi -> identifier (only if doi EXISTS in original)
        if "doi" in original_columns:
            # If identifier wasn't in original, it was added above - now migrate data
            if "identifier" not in original_columns:
                # Migrate existing doi data to identifier (format: doi:xxxxx)
                conn.execute("""
                    UPDATE papers
                    SET identifier = 'doi:' || doi
                    WHERE doi IS NOT NULL AND doi != ''
                """)

            # Drop doi column (must drop index first due to UNIQUE constraint)
            conn.execute("DROP INDEX IF EXISTS idx_papers_doi")
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
