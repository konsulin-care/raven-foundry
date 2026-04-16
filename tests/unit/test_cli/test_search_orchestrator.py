"""Unit tests for search orchestrator.

Run with: pytest tests/unit/test_cli/test_search_orchestrator.py -v
"""

import sqlite3
from unittest.mock import patch

import pytest

from raven.cli.search_orchestrator import (
    LOCAL_MAX_DISTANCE,
    LOCAL_MAX_RESULTS,
    _fetch_local_results,
    _fetch_openalex_results,
    _normalize_local_vector,
    _normalize_openalex,
    _search_openalex,
)


class TestSearchConstants:
    """Tests for search constants."""

    def test_local_max_results_constant(self):
        """Verify local search max results is 10."""
        assert LOCAL_MAX_RESULTS == 10

    def test_local_max_distance_constant(self):
        """Verify local search max distance is 0.1."""
        assert LOCAL_MAX_DISTANCE == 0.1


class TestNormalizeLocalVector:
    """Tests for local vector normalization."""

    def test_normalize_local_vector_converts_distance_to_similarity(self):
        """Verify distance is converted to similarity (1 - distance)."""
        paper = {"title": "Test", "distance": 0.05, "type": "article"}
        result = _normalize_local_vector(paper)

        # distance 0.05 -> similarity 0.95
        assert result["original_score"] == 0.95
        # scaled to 0-1000
        assert result["relevance_score"] == 950.0

    def test_normalize_local_vector_high_distance(self):
        """Verify high distance results in low similarity."""
        paper = {"title": "Test", "distance": 0.5, "type": "article"}
        result = _normalize_local_vector(paper)

        assert result["original_score"] == 0.5
        assert result["relevance_score"] == 500.0


class TestNormalizeOpenAlex:
    """Tests for OpenAlex normalization."""

    def test_normalize_openalex_scales_relevance(self):
        """Verify OpenAlex relevance is scaled to 0-1000."""
        work = {
            "title": "Test Paper",
            "type": "article",
            "relevance_score": 0.75,
            "ids": {"doi": "10.1234/test"},
        }
        result = _normalize_openalex(work)

        assert result["original_score"] == 0.75
        assert result["relevance_score"] == 750.0
        assert result["source"] == "openalex"


class TestSearchOpenAlex:
    """Tests for OpenAlex search."""

    @pytest.fixture
    def db_path_with_papers(self, tmp_path):
        """Create test database with papers."""
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

    def test_search_openalex_calls_api(self, db_path_with_papers, capsys):
        """Verify OpenAlex searches call the API."""
        mock_work = {
            "results": [
                {
                    "title": "Test Paper",
                    "type": "article",
                    "ids": {"doi": "10.1234/test"},
                }
            ],
            "meta": {"count": 1},
        }

        with patch("raven.cli.search_orchestrator.search_works") as mock_search:
            mock_search.return_value = mock_work

            _search_openalex(
                db_path=db_path_with_papers,
                query="test",
                filter_str=None,
                page=1,
                per_page=10,
                sort="relevance_score:desc",
                use_semantic=True,
                text_output=True,
            )

            mock_search.assert_called_once()

    def test_search_openalex_marks_ingested(self, db_path_with_papers, capsys):
        """Verify ingested papers are marked."""
        # Add a paper to local DB
        with sqlite3.connect(db_path_with_papers) as conn:
            conn.execute(
                "INSERT INTO papers (identifier, title) VALUES (?, ?)",
                ("doi:10.1234/test", "Test Paper"),
            )
            conn.commit()

        mock_work = {
            "results": [
                {
                    "title": "Test Paper",
                    "type": "article",
                    "ids": {"doi": "10.1234/test"},
                }
            ],
            "meta": {"count": 1},
        }

        with patch("raven.cli.search_orchestrator.search_works") as mock_search:
            mock_search.return_value = mock_work

            _search_openalex(
                db_path=db_path_with_papers,
                query="test",
                filter_str=None,
                page=1,
                per_page=10,
                sort="relevance_score:desc",
                use_semantic=True,
                text_output=True,
            )

            captured = capsys.readouterr()
            assert "Ingested: Yes" in captured.out


class TestFetchLocalResults:
    """Tests for local result fetching."""

    @pytest.fixture
    def db_path_with_papers(self, tmp_path):
        """Create test database with papers."""
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

    def test_fetch_local_vector_respects_max_results(self, db_path_with_papers):
        """Verify local vector search uses max results limit."""
        mock_embedding = [0.1] * 384

        with (
            patch("raven.cli.search_orchestrator.generate_embedding") as mock_gen,
            patch("raven.cli.search_orchestrator.search_by_embedding") as mock_search,
        ):
            mock_gen.return_value = mock_embedding
            mock_search.return_value = []

            _fetch_local_results(db_path_with_papers, "test", keyword=False)

            # Should call with top_k only
            mock_search.assert_called_once_with(
                db_path_with_papers, mock_embedding, top_k=LOCAL_MAX_RESULTS
            )


class TestFetchOpenAlexResults:
    """Tests for OpenAlex result fetching."""

    def test_fetch_openalex_oversetches(self):
        """Verify OpenAlex search oversetches for pagination."""
        mock_data = {"results": [], "meta": {"count": 0}}

        with patch("raven.cli.search_orchestrator.search_works") as mock_search:
            mock_search.return_value = mock_data

            _fetch_openalex_results(
                query="test",
                filter_str=None,
                page=1,
                per_page=10,
                use_semantic=True,
            )

            # Should oversetch - per_page * 2 or 100, whichever is larger
            call_args = mock_search.call_args
            assert call_args.kwargs["per_page"] >= 100
