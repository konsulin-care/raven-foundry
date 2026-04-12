"""Storage module - SQLite + vector storage for Raven."""

import sqlite3
from pathlib import Path
from typing import Any

# Schema based on AGENTS.md:
# - 384-dim embeddings
# - Metadata (DOI, title, type, timestamps)
# - Enforce DOI uniqueness
# - Use WAL mode for durability
# - Maintain indexes on DOI, type, title


def init_database(db_path: Path) -> None:
    """Initialize the database with schema."""
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doi TEXT UNIQUE NOT NULL COLLATE NOCASE,
                title TEXT NOT NULL,
                type TEXT,
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

        conn.commit()


def search_papers(db_path: Path, query: str) -> list[dict[str, Any]]:
    """Search papers by title or DOI (case-insensitive)."""
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """
            SELECT doi, title, type FROM papers
            WHERE LOWER(title) LIKE LOWER(?) OR LOWER(doi) LIKE LOWER(?)
            LIMIT 50
        """,
            (f"%{query}%", f"%{query}%"),
        )

        results = [dict(row) for row in cursor.fetchall()]

    return results


def add_paper(db_path: Path, doi: str, title: str, type: str = "article") -> None:
    """Add a paper to the database."""
    with sqlite3.connect(db_path) as conn:
        try:
            conn.execute(
                """
                INSERT INTO papers (doi, title, type) VALUES (?, ?, ?)
            """,
                (doi, title, type),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError(f"Paper with DOI {doi} already exists")
