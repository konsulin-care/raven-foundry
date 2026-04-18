"""Integration tests for CLI commands using Click CliRunner.

These tests cover:
- CLI command integration tests with full environment
- Database integration tests
- Ingestion integration tests

Run with: pytest tests/integration/test_cli.py -v
"""

import sqlite3
from unittest.mock import patch

from click.testing import CliRunner

import raven.config
import raven.main
import raven.paths
from raven.storage import add_paper, init_database

# =============================================================================
# CLI Tests using Click CliRunner
# =============================================================================


class TestCLICommands:
    """Tests for raven CLI commands."""

    def test_search_command_no_results(self, tmp_path):
        """Test 'raven search' with no results."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        init_database(db_path)

        # Use --db and --local option to search local database with no matches
        result = runner.invoke(
            raven.main.cli,
            ["search", "--db", str(db_path), "--local", "nonexistent_query_xyz"],
        )

        assert result.exit_code == 0
        # With no embeddings, closest match will be shown with threshold info
        assert "No results found" in result.output

    def test_search_command_with_results(self, tmp_path):
        """Test 'raven search' with results."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "Test Paper Title", "article")

        # Use --db, --local and --local-keyword to search local database
        # (keyword search doesn't require embeddings)
        result = runner.invoke(
            raven.main.cli,
            ["search", "--db", str(db_path), "--local", "--local-keyword", "test"],
        )

        assert result.exit_code == 0
        assert "Test Paper Title" in result.output
        assert "10.1234/test" in result.output
        assert "article" in result.output

    def test_search_command_cli_options(self, tmp_path, monkeypatch):
        """Test 'raven search' with CLI options."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        runner = CliRunner()

        # Mock the OpenAlex API response
        with patch("raven.ingestion.search_works") as mock_search:
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

            # Test with new CLI options (no --local, so uses OpenAlex)
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

    def test_search_command_displays_abstract(self, tmp_path, monkeypatch):
        """Test 'raven search' displays abstract for OpenAlex results."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        runner = CliRunner()

        # Mock OpenAlex API to return results with abstract
        with patch("raven.ingestion.search.search_works") as mock_search:
            mock_search.return_value = {
                "results": [
                    {
                        "title": "Test Paper",
                        "type": "article",
                        "ids": {"doi": "10.1234/test"},
                        "publication_year": 2023,
                        "cited_by_count": 10,
                        "open_access": {"is_oa": True},
                        "relevance_score": 0.9,
                        "abstract": "This is a test abstract for the paper about resilience.",
                        "abstract_inverted_index": {"test": [0], "paper": [1]},
                    }
                ],
                "meta": {"count": 1},
                "search_type": "semantic",
            }

            result = runner.invoke(raven.main.cli, ["search", "resilience"])

            assert result.exit_code == 0
            # Verify abstract appears in JSON output (default is now JSON)
            assert '"abstract":' in result.output

    def test_cache_status_command(self, tmp_path, monkeypatch):
        """Test 'raven cache status' shows cache info."""
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        runner = CliRunner()

        with patch("raven.cli.cache.get_model_cache_size") as mock_size:
            mock_size.return_value = 440401920  # ~420 MB

            result = runner.invoke(raven.main.cli, ["cache", "status"])

            assert result.exit_code == 0
            assert "Cache directory:" in result.output
            assert "Cache size:" in result.output

    def test_cache_status_command_no_cache(self, tmp_path, monkeypatch):
        """Test 'raven cache status' when no cache exists."""
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        runner = CliRunner()

        with patch("raven.cli.cache.get_model_cache_size") as mock_size:
            mock_size.return_value = None

            result = runner.invoke(raven.main.cli, ["cache", "status"])

            assert result.exit_code == 0
            assert "No cache found" in result.output

    def test_cache_clean_command(self, tmp_path, monkeypatch):
        """Test 'raven cache clean' deletes cache."""
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        runner = CliRunner()

        with patch("raven.cli.cache.clean_model_cache") as mock_clean:
            result = runner.invoke(raven.main.cli, ["cache", "clean"])

            assert result.exit_code == 0
            assert "Cache cleaned successfully" in result.output
            mock_clean.assert_called_once()

    def test_init_command(self, tmp_path):
        """Test 'raven init' creates database."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"

        # Use --db option on subcommand
        result = runner.invoke(raven.main.cli, ["init", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Database initialized" in result.output
        assert db_path.exists()

    def test_info_command_no_db(self, tmp_path, monkeypatch):
        """Test 'raven info' when no database exists."""
        runner = CliRunner()
        db_path = tmp_path / "nonexistent.db"

        # Patch where _get_data_dir is used in main.py
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Version:" in result.output
        assert "Total papers indexed: 0" in result.output

    def test_info_command_with_papers(self, tmp_path, monkeypatch):
        """Test 'raven info' with papers in database."""
        runner = CliRunner()
        # info command uses data_dir / "raven.db" by default
        db_path = tmp_path / "raven.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "Test Paper", "article")

        # Patch where _get_data_dir is used in main.py
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Total papers indexed: 1" in result.output

    def test_info_command_db_exists_but_no_papers_table(self, tmp_path, monkeypatch):
        """Test 'raven info' when DB exists but lacks papers table."""
        runner = CliRunner()
        db_path = tmp_path / "raven.db"

        # Create database with a table other than 'papers'
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT, value TEXT)")
            conn.commit()

        # Patch where _get_data_dir is used in main.py
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "'papers' table not found" in result.output
        assert "Total papers indexed: 0" in result.output

    def test_info_command_other_operational_error_re_raised(
        self, tmp_path, monkeypatch
    ):
        """Test 'raven info' re-raises OperationalError for non-missing table errors."""
        import unittest.mock as mock

        runner = CliRunner()
        db_path = tmp_path / "raven.db"

        # Create an empty database file
        db_path.touch()

        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        class MockConn:
            def __init__(self, error_msg):
                self.error_msg = error_msg

            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def execute(self, sql, *args, **kwargs):
                raise sqlite3.OperationalError(self.error_msg)

        # Create mock connection that raises "database is locked" error
        def create_mock_conn(path, **kwargs):
            return MockConn("database is locked")

        with mock.patch("raven.cli.info.sqlite3.connect", side_effect=create_mock_conn):
            result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])

        # Should fail with the OperationalError propagated
        assert result.exit_code == 1
        assert result.exception is not None
        assert isinstance(result.exception, sqlite3.OperationalError)
        assert "database is locked" in str(result.exception)

    def test_ingest_command_success(self, tmp_path, monkeypatch):
        """Test 'raven ingest' with successful API response."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"

        # Set RAVEN_DATA_DIR to our temp directory so the CLI uses it
        monkeypatch.setenv("RAVEN_DATA_DIR", str(tmp_path))

        # Patch ingest_paper to return a successful result
        mock_result = {
            "identifier": "doi:10.1234/test",
            "title": "Test Research Paper",
            "type": "article",
        }
        with patch("raven.cli.ingest.resolve_db_path", return_value=db_path):
            with patch("raven.cli.ingest.ingest_paper", lambda db, doi: mock_result):
                result = runner.invoke(
                    raven.main.cli, ["ingest", "10.1234/test", "--db", str(db_path)]
                )

                assert result.exit_code == 0
                assert "Ingesting: 10.1234/test" in result.output
                assert "Successfully ingested: Test Research Paper" in result.output

    def test_ingest_command_failure(self, tmp_path, monkeypatch):
        """Test 'raven ingest' when API returns failure."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"

        # Set RAVEN_DATA_DIR to our temp directory so the CLI uses it
        monkeypatch.setenv("RAVEN_DATA_DIR", str(tmp_path))

        # Patch ingest_paper to return None (failure case)
        with patch("raven.cli.ingest.resolve_db_path", return_value=db_path):
            with patch("raven.cli.ingest.ingest_paper", lambda db, identifier: None):
                result = runner.invoke(
                    raven.main.cli, ["ingest", "10.9999/failure", "--db", str(db_path)]
                )

                assert result.exit_code == 0
                assert "Ingesting: 10.9999/failure" in result.output
                assert "Failed to ingest publication" in result.output


# =============================================================================
