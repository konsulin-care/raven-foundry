"""Unit tests for add_paper function.

Run with: pytest tests/unit/test_storage/test_add.py -v
"""

import sqlite3

import pytest

from raven.storage import add_paper


class TestAddPaperWithFixture:
    """Tests for add_paper using the test fixture."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema matching production."""
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
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier COLLATE NOCASE)"
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_add_paper_returns_paper_id(self, db_path):
        """add_paper returns the ID of the newly inserted paper."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
            authors="John Doe",
            publication_year=2024,
        )

        assert isinstance(paper_id, int)
        assert paper_id > 0

    def test_add_paper_with_minimal_fields(self, db_path):
        """add_paper works with only required fields."""
        paper_id = add_paper(
            db_path=db_path,
            identifier=None,
            title="Minimal Test Paper",
        )

        assert isinstance(paper_id, int)
        assert paper_id > 0

    def test_add_paper_duplicate_identifier_raises(self, db_path):
        """add_paper raises ValueError for duplicate identifier."""
        # Add first paper
        add_paper(
            db_path=db_path,
            identifier="doi:10.1234/duplicate",
            title="Original Paper",
        )

        # Try to add duplicate - identifier has UNIQUE constraint
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            add_paper(
                db_path=db_path,
                identifier="doi:10.1234/duplicate",
                title="Duplicate Paper",
            )

    def test_add_paper_stores_all_fields(self, db_path):
        """add_paper correctly stores all provided fields."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/full",
            title="Full Test Paper",
            authors="John Doe, Jane Smith",
            abstract="Test abstract",
            publication_year=2024,
            venue="Test Journal",
            openalex_id="https://openalex.org/W123",
            paper_type="article",
        )

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
            row = dict(cursor.fetchone())

        assert row["identifier"] == "doi:10.1234/full"
        assert row["title"] == "Full Test Paper"
        assert row["authors"] == "John Doe, Jane Smith"
        assert row["abstract"] == "Test abstract"
        assert row["publication_year"] == 2024
        assert row["venue"] == "Test Journal"
        assert row["openalex_id"] == "https://openalex.org/W123"
        assert row["type"] == "article"
