"""Integration tests for CLI search/init commands.

Run with: pytest tests/integration/test_cli.py -v
"""

from unittest.mock import patch

from click.testing import CliRunner

import raven.main
from raven.storage import add_paper, init_database


class TestCLISearch:
    """Tests for raven search CLI commands."""

    def test_no_results(self, tmp_path):
        """Test 'raven search' with no results."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        init_database(db_path)
        result = runner.invoke(
            raven.main.cli,
            ["search", "--db", str(db_path), "--local", "nonexistent_query_xyz"],
        )
        assert result.exit_code == 0
        assert "No results found" in result.output

    def test_with_results(self, tmp_path):
        """Test 'raven search' with results."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "Test Paper Title", "article")
        result = runner.invoke(
            raven.main.cli,
            ["search", "--db", str(db_path), "--local", "--local-keyword", "test"],
        )
        assert result.exit_code == 0
        assert "Test Paper Title" in result.output
        assert "10.1234/test" in result.output

    def test_cli_options(self, tmp_path, monkeypatch):
        """Test 'raven search' with CLI options."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")
        runner = CliRunner()
        with patch("raven.cli.search_orchestrator.search_works") as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "doi": "10.1234/test",
                        "title": "Test Paper",
                        "type": "article",
                        "publication_year": 2023,
                        "cited_by_count": 10,
                        "open_access": {"is_oa": True},
                        "relevance_score": 0.9,
                    }
                ],
                "meta": {"count": 1},
                "search_type": "semantic",
            }
            result = runner.invoke(
                raven.main.cli,
                [
                    "search",
                    "--filter",
                    "publication_year:>2020",
                    "--page",
                    "1",
                    "test query",
                ],
            )
            assert result.exit_code == 0

    def test_displays_abstract(self, tmp_path, monkeypatch):
        """Test 'raven search' displays abstract for OpenAlex results."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")
        runner = CliRunner()
        with patch("raven.cli.search_orchestrator.search_works") as mock_search:
            mock_search.return_value = {
                "results": [
                    {  # type: ignore[dict-item]
                        "title": "Test Paper",
                        "type": "article",
                        "ids": {"doi": "10.1234/test"},
                        "publication_year": 2023,
                        "cited_by_count": 10,
                        "open_access": {"is_oa": True},
                        "relevance_score": 0.9,
                        "abstract": "Test abstract about resilience.",
                        "abstract_inverted_index": {"test": [0], "paper": [1]},
                    }
                ],
                "meta": {"count": 1},
                "search_type": "semantic",
            }
            result = runner.invoke(raven.main.cli, ["search", "resilience"])
            assert result.exit_code == 0
            assert '"abstract":' in result.output


class TestCLIInit:
    """Tests for raven init CLI command."""

    def test_init_creates_database(self, tmp_path):
        """Test 'raven init' creates database."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        result = runner.invoke(raven.main.cli, ["init", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "Database initialized" in result.output
        assert db_path.exists()
