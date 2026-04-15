"""Unit tests for vector dimension validation in raven.storage module.

Run with: pytest tests/unit/test_storage/test_vector_dim.py -v
"""

import sqlite3

import pytest

from raven.storage import search_by_embedding


class TestSearchByEmbeddingDimension:
    """Tests for search_by_embedding dimension validation.

    These tests verify dimension checking without requiring vec0.
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

    def test_search_by_embedding_dimension_mismatch(self, db_path):
        """search_by_embedding raises ValueError for wrong dimension."""
        wrong_embedding = [0.1] * 256

        with pytest.raises(ValueError, match="dimension mismatch"):
            search_by_embedding(db_path, wrong_embedding)

    def test_search_by_embedding_dimension_383_raises(self, db_path):
        """search_by_embedding raises for 383 dimensions."""
        wrong_embedding = [0.1] * 383

        with pytest.raises(ValueError, match="dimension mismatch"):
            search_by_embedding(db_path, wrong_embedding)

    def test_search_by_embedding_dimension_385_raises(self, db_path):
        """search_by_embedding raises for 385 dimensions."""
        wrong_embedding = [0.1] * 385

        with pytest.raises(ValueError, match="dimension mismatch"):
            search_by_embedding(db_path, wrong_embedding)
