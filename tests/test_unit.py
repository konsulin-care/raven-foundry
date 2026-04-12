"""Unit tests for Raven Foundry.

These tests cover:
- Config module (environment variable loading)
- CLI commands (using Click CliRunner)
- Ingestion module (API mocking with requests-mock)

Run with: pytest tests/test_unit.py -v
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

import raven.config
import raven.main
from raven.config import (
    get_groq_api_key,
    get_openalex_api_key,
    get_openalex_api_url,
)
from raven.ingestion import ingest_paper
from raven.storage import add_paper, init_database, search_papers

# =============================================================================
# Config Module Tests
# =============================================================================


class TestConfigModule:
    """Tests for raven.config module."""

    def test_get_groq_api_key_from_env_file(self, tmp_path):
        """Config loads GROQ_API_KEY from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("GROQ_API_KEY=test-key-123\n")

        with patch("raven.config._find_env_file", return_value=env_file):
            # Clear cached config
            raven.config._config = {}
            raven.config._load_config()

            assert get_groq_api_key() == "test-key-123"

    def test_get_groq_api_key_missing_raises_error(self, tmp_path):
        """Config raises ValueError when GROQ_API_KEY is missing."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=value\n")

        with patch("raven.config._find_env_file", return_value=env_file):
            raven.config._config = {}
            raven.config._load_config()

            with pytest.raises(ValueError, match="GROQ_API_KEY is not set"):
                get_groq_api_key()

    def test_get_openalex_api_key_from_env_file(self, tmp_path):
        """Config loads OPENALEX_API_KEY from .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENALEX_API_KEY=openalex-key-456\n")

        with patch("raven.config._find_env_file", return_value=env_file):
            raven.config._config = {}
            raven.config._load_config()

            assert get_openalex_api_key() == "openalex-key-456"

    def test_get_openalex_api_key_missing_raises_error(self, tmp_path):
        """Config raises ValueError when OPENALEX_API_KEY is missing."""
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=value\n")

        with patch("raven.config._find_env_file", return_value=env_file):
            raven.config._config = {}
            raven.config._load_config()

            with pytest.raises(ValueError, match="OPENALEX_API_KEY is not set"):
                get_openalex_api_key()

    def test_get_openalex_api_url_defaults_to_production(self, tmp_path):
        """Config defaults OPENALEX_API_URL to production when not set."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENALEX_API_KEY=test\n")  # URL not set

        with patch("raven.config._find_env_file", return_value=env_file):
            raven.config._config = {}
            raven.config._load_config()

            assert get_openalex_api_url() == "https://api.openalex.org"

    def test_get_openalex_api_url_custom(self, tmp_path):
        """Config uses custom OPENALEX_API_URL when set."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OPENALEX_API_KEY=test\nOPENALEX_API_URL=https://custom.example.com\n"
        )

        with patch("raven.config._find_env_file", return_value=env_file):
            raven.config._config = {}
            raven.config._load_config()

            assert get_openalex_api_url() == "https://custom.example.com"

    def test_missing_env_file_returns_empty_config(self):
        """Config handles missing .env file gracefully."""
        with patch("raven.config._find_env_file", return_value=None):
            raven.config._config = {}
            config = raven.config._load_config()

            assert config == {}

    def test_get_data_dir_from_environment(self, monkeypatch):
        """Config uses RAVEN_DATA_DIR when set."""
        monkeypatch.setenv("RAVEN_DATA_DIR", "/custom/data/path")
        raven.config._config = {}  # Reset

        data_dir = raven.config._get_data_dir()
        assert str(data_dir) == "/custom/data/path"

    def test_get_data_dir_with_xdg_home(self, monkeypatch):
        """Config uses XDG_DATA_HOME when set."""
        monkeypatch.delenv("RAVEN_DATA_DIR", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", "/custom/xdg")
        raven.config._config = {}  # Reset

        data_dir = raven.config._get_data_dir()
        assert str(data_dir) == "/custom/xdg/raven"

    def test_find_env_file_in_cwd(self, tmp_path, monkeypatch):
        """Config finds .env in current working directory."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENALEX_API_KEY=test\n")

        # Create a subdirectory and change cwd
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        result = raven.config._find_env_file()
        assert result is not None
        assert result.name == ".env"

    def test_parse_env_file_with_comments(self, tmp_path):
        """Config correctly parses .env with comments and blank lines."""
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\n\nKEY=value\n# Another comment\n")

        result = raven.config._parse_env_file(env_file)
        assert result == {"KEY": "value"}

    def test_parse_env_file_missing_file(self, tmp_path):
        """Config handles missing .env file in _parse_env_file."""
        env_file = tmp_path / "nonexistent.env"

        result = raven.config._parse_env_file(env_file)
        assert result == {}


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

        # Use --db option on subcommand
        result = runner.invoke(
            raven.main.cli, ["search", "--db", str(db_path), "nonexistent"]
        )

        assert result.exit_code == 0
        assert "No results found" in result.output

    def test_search_command_with_results(self, tmp_path):
        """Test 'raven search' with results."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "Test Paper Title", "article")

        # Use --db option on subcommand
        result = runner.invoke(raven.main.cli, ["search", "--db", str(db_path), "test"])

        assert result.exit_code == 0
        assert "Test Paper Title" in result.output
        assert "10.1234/test" in result.output
        assert "article" in result.output

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
        monkeypatch.setattr(raven.main, "_get_data_dir", lambda: tmp_path)

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
        monkeypatch.setattr(raven.main, "_get_data_dir", lambda: tmp_path)

        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "Total papers indexed: 1" in result.output


# =============================================================================
# Ingestion Module Tests with HTTP Mocking
# =============================================================================


class TestIngestionModule:
    """Tests for raven.ingestion module.

    These tests use monkeypatch to set environment variables,
    which is more robust than patching functions because it
    works regardless of where functions are imported.
    """

    def test_ingest_paper_success(self, tmp_path, requests_mock, monkeypatch):
        """Test successful paper ingestion."""
        mock_response = {
            "title": "Sample Research Paper",
            "type": "article",
        }

        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.get(
            "https://api.openalex.org/works/doi:10.1234/sample",
            json=mock_response,
        )

        # Use monkeypatch to set environment variables (more robust)
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "10.1234/sample")

        assert result is not None
        assert result["title"] == "Sample Research Paper"
        assert result["type"] == "article"

    def test_ingest_paper_not_found(self, tmp_path, requests_mock, monkeypatch):
        """Test ingestion returns None when paper not found."""
        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.get(
            "https://api.openalex.org/works/doi:10.9999/missing",
            status_code=404,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "10.9999/missing")

        assert result is None

    def test_doi_cleaning_https_doi_org(self, tmp_path, requests_mock, monkeypatch):
        """Test DOI cleaning removes https://doi.org/ prefix."""
        mock_response = {"title": "Test", "type": "article"}

        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.register_uri(
            "GET",
            "https://api.openalex.org/works/doi:10.1234/test",
            json=mock_response,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Test with URL prefix - should be cleaned to just DOI
        result = ingest_paper(db_path, "https://doi.org/10.1234/test")

        assert result is not None

    def test_doi_cleaning_doi_prefix(self, tmp_path, requests_mock, monkeypatch):
        """Test DOI cleaning removes doi: prefix."""
        mock_response = {"title": "Test", "type": "article"}

        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.register_uri(
            "GET",
            "https://api.openalex.org/works/doi:10.1234/prefix",
            json=mock_response,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "doi:10.1234/prefix")

        assert result is not None
        assert result["doi"] == "10.1234/prefix"


# =============================================================================
# Storage Module Tests
# =============================================================================


class TestStorageModule:
    """Additional tests for raven.storage module."""

    def test_search_case_insensitive(self, tmp_path):
        """Test search is case insensitive."""
        db_path = tmp_path / "test.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "UPPERCASE Title", "article")

        # Search with lowercase
        results = search_papers(db_path, "uppercase")

        assert len(results) == 1
        assert results[0]["title"] == "UPPERCASE Title"

    def test_search_returns_limited_results(self, tmp_path):
        """Test search limits results to 50."""
        db_path = tmp_path / "test.db"
        init_database(db_path)

        # Add many papers
        for i in range(60):
            add_paper(db_path, f"10.1234/{i:03d}", f"Paper {i}", "article")

        results = search_papers(db_path, "Paper")

        assert len(results) == 50  # Limited to 50
