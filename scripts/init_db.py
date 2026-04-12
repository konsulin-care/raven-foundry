#!/usr/bin/env python3
"""
Initialize SQLite database with sqlite-vec extension for vector storage.

Usage:
    python scripts/init_db.py

Creates:
    - data/raven.db - Main SQLite database
    - Vector tables for embeddings storage
"""

import sqlite3
import sys
from pathlib import Path


def get_vec_version(db: sqlite3.Connection) -> str | None:
    """Get sqlite-vec extension version."""
    try:
        result = db.execute("SELECT vec_version()").fetchone()
        return result[0] if result else None
    except sqlite3.OperationalError:
        return None


def init_papers_table(db: sqlite3.Connection) -> None:
    """Create papers table for academic publications."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            openalex_id TEXT UNIQUE,
            title TEXT NOT NULL,
            authors TEXT,
            abstract TEXT,
            publication_year INTEGER,
            doi TEXT,
            venue TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)")


def init_embeddings_table(db: sqlite3.Connection) -> None:
    """Create vector embeddings table using sqlite-vec."""
    db.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS embeddings USING vec0(
            paper_id INTEGER PRIMARY KEY,
            embedding float[768],
            FOREIGN KEY (paper_id) REFERENCES papers(id)
        )
    """)


def init_queries_table(db: sqlite3.Connection) -> None:
    """Create saved queries table for search history."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_text TEXT NOT NULL,
            results_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def init_cache_table(db: sqlite3.Connection) -> None:
    """Create LLM response cache table."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS llm_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT UNIQUE NOT NULL,
            prompt TEXT NOT NULL,
            response TEXT NOT NULL,
            model TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_cache_key ON llm_cache(cache_key)")


def main() -> int:
    """Initialize the database with all required tables."""
    # Ensure data directory exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    db_path = data_dir / "raven.db"
    print(f"Initializing database: {db_path}")

    # Connect to database
    db = sqlite3.connect(db_path)

    try:
        # Enable and load sqlite-vec extension
        db.enable_load_extension(True)

        try:
            import sqlite_vec

            sqlite_vec.load(db)
        except ImportError:
            print("Error: sqlite-vec not installed.", file=sys.stderr)
            print("Install with: pip install sqlite-vec", file=sys.stderr)
            return 1

        db.enable_load_extension(False)

        # Check vec version
        vec_version = get_vec_version(db)
        print(f"sqlite-vec version: {vec_version}")

        # Initialize tables
        init_papers_table(db)
        init_embeddings_table(db)
        init_queries_table(db)
        init_cache_table(db)

        db.commit()
        print("Database initialized successfully!")

        # Verify tables
        cursor = db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' OR type='virtual table'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables: {', '.join(tables)}")

        return 0

    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
