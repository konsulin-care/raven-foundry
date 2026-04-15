"""Unit tests for search orchestrator fallback logic in CLI.

Run with: pytest tests/unit/test_cli/test_search_orchestrator.py -v
"""

import sqlite3
from unittest.mock import patch

import pytest

from raven.cli.search_orchestrator import (
    _display_local_results,
    _print_openalex_result,
    _search_local_only,
    _search_openalex,
    _try_local_keyword_then_openalex,
    _try_local_vector_then_openalex,
)


class TestSearchWithFallback:
    """Tests for search fallback behavior."""

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

    def test_search_with_fallback_local_only_vector(self, db_path, capsys):
        """Verify local vector only when --local flag (no --keyword).

        Tests that when --local is set without --keyword, the function
        performs local vector search only, with no OpenAlex fallback.
        """
        query = "machine learning"
        mock_embedding = [0.1] * 384

        with (
            patch("raven.embeddings.generate_embedding") as mock_gen_emb,
            patch("raven.storage.embedding.search_by_embedding") as mock_search_emb,
        ):
            mock_gen_emb.return_value = mock_embedding
            mock_search_emb.return_value = []

            _search_local_only(db_path, query, keyword=False)

            # Verify vector search was called (no keyword, no fallback)
            mock_gen_emb.assert_called_once_with(query)
            mock_search_emb.assert_called_once_with(db_path, mock_embedding)

            # Should show no results message (no fallback to OpenAlex)
            captured = capsys.readouterr()
            assert "No results found in local database" in captured.out

    def test_search_with_fallback_local_only_keyword(self, db_path, capsys):
        """Verify local keyword only when --local --keyword flags.

        Tests that when both --local and --keyword are set, the function
        performs local keyword search only, with no OpenAlex fallback.
        """
        query = "machine learning"

        with patch("raven.storage.paper.search_papers") as mock_search_papers:
            mock_search_papers.return_value = []

            _search_local_only(db_path, query, keyword=True)

            # Verify keyword search was called (local only, no fallback)
            mock_search_papers.assert_called_once_with(db_path, query)

            # Should show no results message (no fallback to OpenAlex)
            captured = capsys.readouterr()
            assert "No results found in local database" in captured.out

    def test_search_with_fallback_vector_fallback(self, db_path, capsys):
        """Verify local vector → OpenAlex fallback when no --local.

        Tests that when neither --local nor --keyword is set,
        the function tries local vector first, then falls back to
        OpenAlex semantic search when no local results found.
        """
        query = "machine learning"
        mock_embedding = [0.1] * 384

        with (
            patch("raven.embeddings.generate_embedding") as mock_gen_emb,
            patch("raven.storage.embedding.search_by_embedding") as mock_search_emb,
            patch("raven.cli.search_orchestrator._search_openalex") as mock_openalex,
        ):
            mock_gen_emb.return_value = mock_embedding
            mock_search_emb.return_value = []  # No local results
            mock_openalex.return_value = None

            _try_local_vector_then_openalex(
                db_path, query, filter_str=None, page=1, per_page=10, sort="relevance"
            )

            # Verify local vector search was tried first
            mock_gen_emb.assert_called_once_with(query)
            mock_search_emb.assert_called_once_with(db_path, mock_embedding)

            # Verify fallback to OpenAlex was triggered
            captured = capsys.readouterr()
            assert (
                "No local results. Falling back to OpenAlex semantic search"
                in captured.out
            )
            mock_openalex.assert_called_once()

    def test_search_with_fallback_keyword_fallback(self, db_path, capsys):
        """Verify local keyword → OpenAlex keyword fallback when --keyword (no --local).

        Tests that when --keyword is set without --local, the function
        tries local keyword search first, then falls back to OpenAlex
        keyword search when no local results found.
        """
        query = "machine learning"

        with (
            patch("raven.storage.paper.search_papers") as mock_search_papers,
            patch("raven.cli.search_orchestrator._search_openalex") as mock_openalex,
        ):
            mock_search_papers.return_value = []  # No local results
            mock_openalex.return_value = None

            _try_local_keyword_then_openalex(
                db_path, query, filter_str=None, page=1, per_page=10, sort="relevance"
            )

            # Verify local keyword search was tried first
            mock_search_papers.assert_called_once_with(db_path, query)

            # Verify fallback to OpenAlex was triggered
            captured = capsys.readouterr()
            assert (
                "No local results. Falling back to OpenAlex keyword search"
                in captured.out
            )
            mock_openalex.assert_called_once()

    def test_display_local_results_omits_missing_fields(self, capsys):
        """Verify missing fields are omitted in local results display.

        Tests that when a paper has missing optional fields like
        identifier, year, or abstract, those fields are not displayed.
        """
        # Result with only required fields
        results = [
            {
                "id": 1,
                "title": "Test Paper Title",
                "type": "article",
                # Missing: identifier, publication_year, abstract
            }
        ]

        _display_local_results(results, show_relevance=False)

        captured = capsys.readouterr()
        output = captured.out

        # Should show title
        assert "Test Paper Title" in output

        # Should NOT show identifier (missing)
        assert "Identifier:" not in output

        # Should NOT show year (missing)
        assert "Year:" not in output

        # Should show type (has value)
        assert "Type: article" in output

        # Should NOT show abstract (missing)
        assert "Abstract:" not in output


class TestSearchOrchestratorWithResults:
    """Tests for search orchestrator when results are found locally."""

    def test_vector_fallback_skips_openalex_when_local_results_exist(
        self, tmp_path, capsys
    ):
        """Verify OpenAlex is NOT called when local results exist."""
        db_path = tmp_path / "test.db"

        # Create minimal database
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    type TEXT DEFAULT 'article'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()

        query = "test query"
        mock_embedding = [0.1] * 384
        mock_results = [
            {
                "id": 1,
                "title": "Local Paper",
                "identifier": "doi:10.1234/test",
                "type": "article",
                "relevance_score": 0.95,
            }
        ]

        with (
            patch("raven.embeddings.generate_embedding") as mock_gen_emb,
            patch("raven.storage.embedding.search_by_embedding") as mock_search_emb,
            patch("raven.cli.search_orchestrator._search_openalex") as mock_openalex,
        ):
            mock_gen_emb.return_value = mock_embedding
            mock_search_emb.return_value = mock_results
            mock_openalex.return_value = None

            _try_local_vector_then_openalex(
                db_path, query, filter_str=None, page=1, per_page=10, sort="relevance"
            )

            # Verify local search returned results
            mock_search_emb.assert_called_once()

            # Verify OpenAlex was NOT called (fallback skipped)
            mock_openalex.assert_not_called()

            # Verify results were displayed
            captured = capsys.readouterr()
            assert "Local Paper" in captured.out


class TestSearchOpenAlex:
    """Tests for _search_openalex and _print_openalex_result functions."""

    def test_search_openalex_calls_search_works(self, capsys):
        """Verify _search_openalex calls search_works with correct params."""
        with (
            patch("raven.ingestion.search_works") as mock_search_works,
            patch("raven.ingestion.format_search_result") as mock_format,
        ):
            mock_search_works.return_value = {
                "results": [{"id": 1, "title": "Test"}],
                "meta": {"count": 1},
                "search_type": "semantic",
            }
            mock_format.return_value = {"title": "Test", "type": "article"}

            _search_openalex("query", None, 1, 10, "relevance", use_semantic=True)

            mock_search_works.assert_called_once_with(
                query="query",
                filter_str=None,
                page=1,
                per_page=10,
                sort="relevance",
                use_semantic=True,
            )

    def test_search_openalex_no_results(self, capsys):
        """Verify message when no results found."""
        with patch("raven.ingestion.search_works") as mock_search_works:
            mock_search_works.return_value = {
                "results": [],
                "meta": {},
                "search_type": "semantic",
            }

            _search_openalex("query", None, 1, 10, "relevance", use_semantic=True)

            captured = capsys.readouterr()
            assert "No results found" in captured.out

    def test_search_openalex_displays_results(self, capsys):
        """Verify _search_openalex displays result metadata."""
        with (
            patch("raven.ingestion.search_works") as mock_search_works,
            patch("raven.ingestion.format_search_result") as mock_format,
        ):
            mock_search_works.return_value = {
                "results": [{"id": 1}],
                "meta": {"count": 1},
                "search_type": "semantic",
            }
            mock_format.return_value = {"title": "Test Paper", "type": "article"}

            _search_openalex("query", None, 1, 10, "relevance", use_semantic=True)

            captured = capsys.readouterr()
            output = captured.out
            assert "Search type: semantic" in output
            assert "Total results: 1" in output
            assert "Test Paper" in output
            assert "raven ingest" in output

    def test_print_openalex_result_with_all_fields(self, capsys):
        """Verify _print_openalex_result displays all fields correctly."""
        formatted = {
            "title": "Test Paper",
            "identifier": "doi:10.1234/test",
            "publication_year": 2024,
            "type": "article",
            "cited_by_count": 100,
            "open_access": True,
            "relevance_score": 0.95,
            "abstract": "Test abstract" * 100,  # Long abstract
        }

        _print_openalex_result(1, formatted)

        captured = capsys.readouterr()
        output = captured.out
        assert "Test Paper" in output
        assert "doi:10.1234/test" in output
        assert "2024" in output
        assert "100" in output  # citations
        assert "0.950" in output  # relevance
        assert "Open Access: Yes" in output
        assert "..." in output  # abstract truncated

    def test_print_openalex_result_minimal_fields(self, capsys):
        """Verify _print_openalex_result handles minimal fields."""
        formatted = {
            "title": "Minimal Paper",
            "type": "article",
            # Missing: identifier, year, citations, etc.
        }

        _print_openalex_result(2, formatted)

        captured = capsys.readouterr()
        output = captured.out
        assert "Minimal Paper" in output
        assert "Type: article" in output
        assert "Identifier:" not in output
        assert "Year:" not in output
        assert "Citations:" not in output

    def test_print_openalex_result_abstract_truncation(self, capsys):
        """Verify abstract is truncated to 300 chars."""
        short_abstract = "Short abstract"
        long_abstract = "A" * 400

        # Short abstract - no truncation
        _print_openalex_result(
            1, {"title": "Short", "type": "article", "abstract": short_abstract}
        )
        captured = capsys.readouterr()
        assert "Short abstract" in captured.out
        assert "..." not in captured.out

        # Long abstract - should be truncated
        _print_openalex_result(
            2, {"title": "Long", "type": "article", "abstract": long_abstract}
        )
        captured = capsys.readouterr()
        assert "..." in captured.out
        assert (
            len(captured.out.split("Abstract: ")[1].split("---")[0].strip()) == 303
        )  # 300 + "..."
