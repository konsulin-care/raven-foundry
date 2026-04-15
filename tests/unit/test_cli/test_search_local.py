"""Unit tests for local search functionality in CLI search_orchestrator.py.

Run with: pytest tests/unit/test_cli/test_search_local.py -v

Note: These tests cover the local-only search behaviors (--local flag).
Core fallback logic is tested in test_search_orchestrator.py.
"""

import sqlite3
from unittest.mock import patch

import pytest

from raven.cli.search_orchestrator import _search_local_only


class TestSearchLocalOnly:
    """Tests for the _search_local_only function (--local flag behavior)."""

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

    def test_search_local_vector_by_default(self, db_path, capsys):
        """Verify vector search is called when --keyword flag is not set.

        Tests that when keyword=False (default), the function calls
        generate_embedding and search_by_embedding instead of search_papers.
        """
        query = "machine learning"

        # Mock the heavy embedding modules
        mock_embedding = [0.1] * 384

        with (
            patch("raven.cli.search_orchestrator.generate_embedding") as mock_gen_emb,
            patch(
                "raven.cli.search_orchestrator.search_by_embedding"
            ) as mock_search_emb,
        ):
            mock_gen_emb.return_value = mock_embedding
            mock_search_emb.return_value = []

            _search_local_only(db_path, query, keyword=False)

            # Verify vector search was called (default behavior)
            mock_gen_emb.assert_called_once_with(query)
            mock_search_emb.assert_called_once_with(db_path, mock_embedding)

    def test_search_local_keyword_with_flag(self, db_path, capsys):
        """Verify keyword search is called when --keyword flag is set.

        Tests that when keyword=True, the function calls
        search_papers instead of vector search.
        """
        query = "machine learning"

        with patch("raven.cli.search_orchestrator.search_papers") as mock_search_papers:
            mock_search_papers.return_value = []

            _search_local_only(db_path, query, keyword=True)

            # Verify keyword search was called
            mock_search_papers.assert_called_once_with(db_path, query)

    def test_search_local_no_embeddings(self, db_path, capsys):
        """Verify empty results don't cause errors.

        Tests that when vector search returns no results,
        the function displays a user-friendly message and doesn't raise.
        """
        query = "nonexistent topic"

        mock_embedding = [0.1] * 384

        with (
            patch("raven.cli.search_orchestrator.generate_embedding") as mock_gen_emb,
            patch(
                "raven.cli.search_orchestrator.search_by_embedding"
            ) as mock_search_emb,
        ):
            mock_gen_emb.return_value = mock_embedding
            mock_search_emb.return_value = []

            _search_local_only(db_path, query, keyword=False)

            # Should complete without error and print "No results found"
            captured = capsys.readouterr()
            assert "No results found in local database" in captured.out

    def test_search_local_keyword_no_results(self, db_path, capsys):
        """Verify keyword search handles empty results properly."""
        query = "nonexistent topic"

        with patch("raven.cli.search_orchestrator.search_papers") as mock_search_papers:
            mock_search_papers.return_value = []

            _search_local_only(db_path, query, keyword=True)

            captured = capsys.readouterr()
            assert "No results found in local database" in captured.out

    def test_search_local_vector_with_results(self, db_path, capsys):
        """Verify vector search displays results when found."""
        query = "test query"
        mock_embedding = [0.1] * 384

        mock_results = [
            {
                "id": 1,
                "title": "Test Paper Title",
                "identifier": "doi:10.1234/test",
                "type": "article",
                "relevance_score": 0.95,
            }
        ]

        with (
            patch("raven.cli.search_orchestrator.generate_embedding") as mock_gen_emb,
            patch(
                "raven.cli.search_orchestrator.search_by_embedding"
            ) as mock_search_emb,
        ):
            mock_gen_emb.return_value = mock_embedding
            mock_search_emb.return_value = mock_results

            _search_local_only(db_path, query, keyword=False)

            captured = capsys.readouterr()
            assert "Test Paper Title" in captured.out

    def test_search_local_keyword_with_results(self, db_path, capsys):
        """Verify keyword search displays results when found."""
        query = "test query"

        mock_results = [
            {
                "id": 1,
                "title": "Test Paper Title",
                "identifier": "doi:10.1234/test",
                "type": "article",
            }
        ]

        with patch("raven.cli.search_orchestrator.search_papers") as mock_search_papers:
            mock_search_papers.return_value = mock_results

            _search_local_only(db_path, query, keyword=True)

            captured = capsys.readouterr()
            assert "Test Paper Title" in captured.out
