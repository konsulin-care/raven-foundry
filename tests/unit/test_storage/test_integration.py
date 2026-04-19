"""Integration tests combining multiple functions.

Run with: pytest tests/unit/test_storage/test_integration.py -v
"""

import sqlite3

import pytest

from raven.storage import add_paper, search_papers


class TestIntegrationWithFixture:
    """Integration tests combining multiple functions."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    year INTEGER,
                    source TEXT,
                    type TEXT DEFAULT 'article',
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

    def test_add_paper_and_retrieve(self, db_path):
        """Add paper and retrieve it."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
            authors="Test Author",
            year=2024,
        )

        results = search_papers(db_path, "test")

        assert len(results) == 1
        assert results[0]["id"] == paper_id

    def test_add_multiple_papers(self, db_path):
        """Add multiple papers with different identifiers."""
        paper_ids = []
        for i in range(3):
            pid = add_paper(
                db_path=db_path,
                identifier=f"doi:10.1234/test{i}",
                title=f"Paper {i}",
            )
            paper_ids.append(pid)

        assert len(paper_ids) == 3
        assert len(set(paper_ids)) == 3  # All unique

    def test_search_empty_db(self, db_path):
        """Search on empty database returns empty list."""
        results = search_papers(db_path, "anything")

        assert results == []
