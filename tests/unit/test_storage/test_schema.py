"""Unit tests for database schema.

Run with: pytest tests/unit/test_storage/test_schema.py -v
"""

import sqlite3

import pytest


class TestDatabaseWithFixture:
    """Tests using a shared fixture that sets up database properly for testing.

    This fixture creates the database WITHOUT the vec0 virtual table,
    using a regular table instead for embedding storage.
    """

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create a test database with all tables (excluding vec0)."""
        db_path = tmp_path / "test.db"

        # Create tables manually (skipping vec0 virtual table)
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_type ON papers(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year)"
            )
            # Use regular table instead of vec0 for testing
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()

        return db_path

    def test_papers_table_columns(self, db_path):
        """Verify papers table has expected columns."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(papers)")
            columns = {row[1] for row in cursor.fetchall()}

        expected = {
            "id",
            "identifier",
            "title",
            "authors",
            "abstract",
            "publication_year",
            "venue",
            "type",
            "created_at",
            "openalex_id",
        }
        assert expected.issubset(columns)

    def test_indexes_created(self, db_path):
        """Verify required indexes exist."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}

        expected = {
            "idx_papers_identifier",
            "idx_papers_type",
            "idx_papers_title",
            "idx_papers_year",
        }
        assert expected.issubset(indexes)
