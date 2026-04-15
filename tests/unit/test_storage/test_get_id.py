"""Unit tests for search_papers function.

Run with: pytest tests/unit/test_storage/test_search.py -v
"""

import sqlite3

import pytest

from raven.storage import add_paper, search_papers


class TestSearchPapersWithFixture:
    """Tests for search_papers using the test fixture."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema."""
        db_path = tmp_path / "test.db"
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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_search_papers_by_title(self, db_path):
        """search_papers finds papers by title."""
        add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Machine Learning Advances",
        )

        results = search_papers(db_path, "machine learning")

        assert len(results) == 1
        assert results[0]["title"] == "Machine Learning Advances"

    def test_search_papers_by_identifier(self, db_path):
        """search_papers finds papers by identifier."""
        add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        results = search_papers(db_path, "10.1234")

        assert len(results) == 1
        assert results[0]["identifier"] == "doi:10.1234/test"

    def test_search_papers_no_results(self, db_path):
        """search_papers returns empty list when no matches."""
        results = search_papers(db_path, "nonexistent")

        assert results == []
