"""Unit tests for embedding operations in raven.storage module.

Run with: pytest tests/unit/test_storage/test_embedding.py -v
"""

import sqlite3

import pytest

from raven.storage import add_embedding, add_paper


class TestAddEmbeddingWithFixture:
    """Tests for add_embedding using the test fixture."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    year INTEGER,
                    source TEXT,
                    type TEXT DEFAULT 'article',
                    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    text TEXT,
                    type TEXT,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_add_embedding_valid_paper(self, db_path):
        """add_embedding adds embedding for valid paper_id."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        embedding = [0.1] * 384

        # Should not raise ValueError
        add_embedding(db_path, paper_id, embedding, text="Test Paper", type="title")

    def test_add_embedding_dimension_mismatch(self, db_path):
        """add_embedding raises ValueError for wrong dimension."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        # Wrong dimension (not 384)
        wrong_embedding = [0.1] * 256

        with pytest.raises(ValueError, match="dimension mismatch"):
            add_embedding(
                db_path, paper_id, wrong_embedding, text="Test Paper", type="title"
            )

    def test_add_embedding_dimension_383_raises(self, db_path):
        """add_embedding raises for 383-dimensional vector."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        wrong_embedding = [0.1] * 383

        with pytest.raises(ValueError, match="dimension mismatch"):
            add_embedding(
                db_path, paper_id, wrong_embedding, text="Test Paper", type="title"
            )

    def test_add_embedding_dimension_385_raises(self, db_path):
        """add_embedding raises for 385-dimensional vector."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        wrong_embedding = [0.1] * 385

        with pytest.raises(ValueError, match="dimension mismatch"):
            add_embedding(
                db_path, paper_id, wrong_embedding, text="Test Paper", type="title"
            )
