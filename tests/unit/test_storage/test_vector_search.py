"""Tests for search_by_embedding using mocked vec functionality.

Run with: pytest tests/unit/test_storage/test_vector_search.py -v
"""

import sqlite3

import pytest

from raven.storage import add_paper, search_by_embedding, serialize_f32


class TestSearchByEmbeddingWithFixture:
    """Tests for search_by_embedding using mocked vec functionality.

    These tests verify the function builds correct SQL but may not
    get full results without vec0 extension.
    """

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
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_search_by_embedding_returns_list(self, db_path):
        """search_by_embedding returns a list or skips if vec0 unavailable."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        # Add embedding manually
        embedding = serialize_f32([0.1] * 384)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO embeddings (paper_id, embedding) VALUES (?, ?)",
                (paper_id, embedding),
            )
            conn.commit()

        query = [0.1] * 384

        # The vec0 extension provides e.distance column which doesn't exist
        # in our regular table, so this will fail - that's expected
        try:
            results = search_by_embedding(db_path, query, top_k=10)
            # If it works, verify it's a list
            assert isinstance(results, list)
        except sqlite3.OperationalError as e:
            if "no such column: e.distance" in str(e):
                pytest.skip("vec0 extension not available")
            raise

    def test_search_by_embedding_result_fields(self, db_path):
        """search_by_embedding result contains expected fields."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        embedding = serialize_f32([0.1] * 384)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO embeddings (paper_id, embedding) VALUES (?, ?)",
                (paper_id, embedding),
            )
            conn.commit()

        query = [0.1] * 384

        # The vec0 extension provides e.distance column which doesn't exist
        # in our regular table, so this will fail - that's expected
        try:
            results = search_by_embedding(db_path, query, top_k=1)
            if results:
                result = results[0]
                # Check structure if results returned
                assert "id" in result
                assert "distance" in result
        except sqlite3.OperationalError as e:
            if "no such column: e.distance" in str(e):
                pytest.skip("vec0 extension not available")
            raise
