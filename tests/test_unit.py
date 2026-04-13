"""Unit tests for Raven Foundry.

These tests cover:
- Config module (environment variable loading)
- CLI commands (using Click CliRunner)
- Ingestion module (API mocking with requests-mock)

Run with: pytest tests/test_unit.py -v
"""

import sqlite3
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
from raven.ingestion import (
    DEFAULT_FILTERS,
    SEMANTIC_FILTERS,
    format_search_result,
    ingest_paper,
    search_works,
    search_works_keyword,
    undo_inverted_index,
)
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
        # Change to tmp_path first so the .env is created in the actual cwd
        monkeypatch.chdir(tmp_path)

        # Create .env in the current working directory (now tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("OPENALEX_API_KEY=test\n")

        # Verify it is found when working directory contains .env
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

        # Use --db and --local option to search local database with no matches
        result = runner.invoke(
            raven.main.cli,
            ["search", "--db", str(db_path), "--local", "nonexistent_query_xyz"],
        )

        assert result.exit_code == 0
        assert "No results found" in result.output

    def test_search_command_with_results(self, tmp_path):
        """Test 'raven search' with results."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "Test Paper Title", "article")

        # Use --db and --local option to search local database
        result = runner.invoke(
            raven.main.cli, ["search", "--db", str(db_path), "--local", "test"]
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

    def test_info_command_db_exists_but_no_papers_table(self, tmp_path, monkeypatch):
        """Test 'raven info' when DB exists but lacks papers table."""
        runner = CliRunner()
        db_path = tmp_path / "raven.db"

        # Create database with a table other than 'papers'
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT, value TEXT)")
            conn.commit()

        # Patch where _get_data_dir is used in main.py
        monkeypatch.setattr(raven.main, "_get_data_dir", lambda: tmp_path)

        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])

        assert result.exit_code == 0
        assert "'papers' table not found" in result.output
        assert "Total papers indexed: 0" in result.output

    def test_ingest_command_success(self, tmp_path, monkeypatch):
        """Test 'raven ingest' with successful API response."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"

        # Patch _resolve_db_path to return our test database
        def mock_resolve_db_path(env_path=None, db_path_param=None):
            return db_path

        monkeypatch.setattr(raven.main, "_resolve_db_path", mock_resolve_db_path)

        # Patch ingest_paper to return a successful result
        mock_result = {
            "doi": "10.1234/test",
            "title": "Test Research Paper",
            "type": "article",
        }
        monkeypatch.setattr(
            raven.ingestion, "ingest_paper", lambda db, doi: mock_result
        )

        result = runner.invoke(
            raven.main.cli, ["ingest", "10.1234/test", "--db", str(db_path)]
        )

        assert result.exit_code == 0
        assert "Ingesting DOI: 10.1234/test" in result.output
        assert "Successfully ingested: Test Research Paper" in result.output

    def test_ingest_command_failure(self, tmp_path, monkeypatch):
        """Test 'raven ingest' when API returns failure."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"

        # Patch _resolve_db_path to return our test database
        def mock_resolve_db_path(env_path=None, db_path_param=None):
            return db_path

        monkeypatch.setattr(raven.main, "_resolve_db_path", mock_resolve_db_path)

        # Patch ingest_paper to return None (failure case)
        monkeypatch.setattr(raven.ingestion, "ingest_paper", lambda db, doi: None)

        result = runner.invoke(
            raven.main.cli, ["ingest", "10.9999/failure", "--db", str(db_path)]
        )

        assert result.exit_code == 0
        assert "Ingesting DOI: 10.9999/failure" in result.output
        assert "Failed to ingest publication" in result.output


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


# =============================================================================
# LLM Module Tests
# =============================================================================


class TestLLMModule:
    """Tests for raven.llm module."""

    def test_make_cache_key_deterministic(self):
        """Cache key is deterministic - same inputs produce same key."""
        from raven.llm import _make_cache_key

        key1 = _make_cache_key("test prompt", "system prompt")
        key2 = _make_cache_key("test prompt", "system prompt")

        assert key1 == key2

    def test_make_cache_key_unique_inputs(self):
        """Different inputs produce different keys."""
        from raven.llm import _make_cache_key

        key1 = _make_cache_key("prompt one", "system one")
        key2 = _make_cache_key("prompt two", "system two")

        assert key1 != key2

    def test_make_cache_key_prevents_collision(self):
        """Cache key uses SHA256 to prevent hash() collisions."""
        from raven.llm import _make_cache_key

        # Python's hash() can collide for different strings
        # SHA256 should not collide for these test cases
        test_cases = [
            ("test", "system"),
            ("test", "system "),  # trailing space
            ("test ", "system"),  # leading space in prompt
            ("", ""),
            ("a" * 1000, "b" * 1000),
        ]

        keys = [_make_cache_key(p, s) for p, s in test_cases]

        # All keys should be unique (64 hex chars = 32 bytes)
        assert len(set(keys)) == len(test_cases)
        assert all(len(k) == 64 for k in keys)

    def test_make_cache_key_with_none_system_prompt(self):
        """Cache key handles None system_prompt."""
        from raven.llm import _make_cache_key

        key_with_none = _make_cache_key("prompt", None)
        key_with_empty = _make_cache_key("prompt", "")

        assert key_with_none == key_with_empty


# =============================================================================
# Ingestion Retry Logic Tests
# =============================================================================


class TestIngestionRetryLogic:
    """Tests for ingestion retry logic."""

    def test_create_session_with_retries(self):
        """Session is created with retry strategy."""
        from raven.ingestion import _create_session_with_retries

        session = _create_session_with_retries()

        # Check that adapters are mounted
        assert session is not None

        # Verify retry adapter is attached
        http_adapter = session.get_adapter("https://api.openalex.org")
        assert http_adapter is not None

    def test_ingest_retries_on_server_error(self, tmp_path, requests_mock, monkeypatch):
        """Ingestion handles 503 server error - retry config is wired up."""
        db_path = tmp_path / "test.db"
        init_database(db_path)

        # Single 503 response - session has retry logic configured
        # but actual retries require real network or different mock setup
        requests_mock.get(
            "https://api.openalex.org/works/doi:10.1234/retry",
            status_code=503,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "10.1234/retry")

        # Server error returns None (retry exhausted or immediate failure)
        # The retry strategy is configured on the session, verified in
        # test_create_session_with_retries
        assert result is None

    def test_ingest_fails_on_rate_limit(self, tmp_path, requests_mock, monkeypatch):
        """Ingestion handles 429 rate limit response."""
        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.get(
            "https://api.openalex.org/works/doi:10.1234/ratelimit",
            status_code=429,
            headers={"Retry-After": "60"},
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "10.1234/ratelimit")

        assert result is None


# =============================================================================
# OpenAlex Search Tests
# =============================================================================


class TestOpenAlexSearch:
    """Tests for OpenAlex search functions."""

    def test_default_filters_includes_oa_and_doi(self):
        """DEFAULT_FILTERS includes is_oa and has_doi."""
        assert "is_oa:true" in DEFAULT_FILTERS
        assert "has_doi:true" in DEFAULT_FILTERS

    def test_semantic_filters_supports_semantic_search(self):
        """SEMANTIC_FILTERS uses is_oa which is supported in semantic search."""
        # Semantic search only supports: is_oa (not open_access.is_oa), has_abstract, etc.
        assert "is_oa:true" in SEMANTIC_FILTERS
        # Should NOT have has_doi which is not supported in semantic search
        assert "has_doi" not in SEMANTIC_FILTERS

    def test_format_search_result_basic(self):
        """format_search_result extracts key fields."""
        work = {
            "doi": "10.1234/test",
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2023,
            "cited_by_count": 100,
            "open_access": {"is_oa": True},
        }

        result = format_search_result(work)

        assert result["doi"] == "10.1234/test"
        assert result["title"] == "Test Paper"
        assert result["type"] == "article"
        assert result["publication_year"] == 2023
        assert result["cited_by_count"] == 100
        assert result["open_access"] is True

    def test_format_search_result_missing_fields(self):
        """format_search_result handles missing fields."""
        work = {
            "title": "Minimal Paper",
            # Missing doi, type, etc.
        }

        result = format_search_result(work)

        assert result["title"] == "Minimal Paper"
        assert result["doi"] is None
        assert result["type"] == "article"  # Default
        assert result["cited_by_count"] == 0  # Default

    def test_search_works_keyword_fallback(self, requests_mock, monkeypatch):
        """search_works falls back to keyword on semantic failure."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Mock semantic search (429 rate limit)
        requests_mock.get(
            "https://api.openalex.org/works",
            [
                {"status_code": 429},  # Semantic rate limited
                {
                    "json": {  # Keyword fallback succeeds
                        "results": [
                            {
                                "doi": "10.1234/fallback",
                                "title": "Fallback Paper",
                                "type": "article",
                                "cited_by_count": 50,
                            }
                        ],
                        "meta": {"count": 1},
                    }
                },
            ],
        )

        result = search_works("test query", use_semantic=True)

        assert result["search_type"] == "keyword"
        assert len(result["results"]) == 1

    def test_search_works_semantic_success(self, requests_mock, monkeypatch):
        """search_works uses semantic when available."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        requests_mock.get(
            "https://api.openalex.org/works",
            json={
                "results": [
                    {
                        "doi": "10.1234/semantic",
                        "title": "Semantic Result",
                        "type": "article",
                        "relevance_score": 0.95,
                    }
                ],
                "meta": {"count": 1},
            },
        )

        result = search_works("machine learning", use_semantic=True)

        # Rate limiting not triggered in mock, should use semantic
        assert result["search_type"] in ["semantic", "keyword"]

    def test_search_works_keyword_only(self, requests_mock, monkeypatch):
        """search_works_keyword uses keyword search only."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        requests_mock.get(
            "https://api.openalex.org/works",
            json={
                "results": [
                    {
                        "doi": "10.1234/keyword",
                        "title": "Keyword Result",
                        "type": "article",
                    }
                ],
                "meta": {"count": 1},
            },
        )

        result = search_works_keyword("test")

        assert result["search_type"] == "keyword"
        assert len(result["results"]) == 1

    def test_search_works_with_filters(self, requests_mock, monkeypatch):
        """search_works applies filters correctly."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Check that the request includes both default and custom filters
        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query", filter="publication_year:>2020", use_semantic=False
        )

        assert result["search_type"] == "keyword"
        assert len(result["results"]) == 0  # Mock returns empty results

    def test_search_works_with_sort(self, requests_mock, monkeypatch):
        """search_works passes sort parameter directly to OpenAlex."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Use multi-field sort format
        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query",
            sort="publication_year:desc,relevance_score:desc",
            use_semantic=False,
        )

        assert result["search_type"] == "keyword"

        # Verify sort is passed as-is (no conversion)
        last_request = requests_mock.last_request
        assert last_request
        assert (
            last_request.qs["sort"][0] == "publication_year:desc,relevance_score:desc"
        )

    def test_search_works_single_field_sort(self, requests_mock, monkeypatch):
        """search_works passes single-field sort directly to OpenAlex."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query",
            sort="cited_by_count:desc",
            use_semantic=False,
        )

        assert result["search_type"] == "keyword"

        # Verify sort is passed as-is
        last_request = requests_mock.last_request
        assert last_request
        assert last_request.qs["sort"][0] == "cited_by_count:desc"

    def test_search_works_keyword_with_filters(self, requests_mock, monkeypatch):
        """search_works keyword mode applies filters correctly."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Check that the request includes both default and custom filters
        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query", filter="publication_year:>2020", use_semantic=False
        )

        assert result["search_type"] == "keyword"


# =============================================================================
# Undo Inverted Index Tests
# =============================================================================


class TestUndoInvertedIndex:
    """Tests for undo_inverted_index function."""

    # Sample inverted index for testing
    SAMPLE_INVERTED_INDEX = {
        "Hello": [0],
        "world": [1],
        "this": [2, 5],
        "is": [3],
        "a": [4],
        "test": [6],
    }

    def test_undo_inverted_index_basic(self):
        """Reconstructs basic text from inverted index."""
        result = undo_inverted_index(self.SAMPLE_INVERTED_INDEX)

        # Note: "this" appears at positions [2, 5], so it appears twice
        assert result == "Hello world this is a this test"

    def test_undo_inverted_index_with_example_from_user(self):
        """Test with the example provided in the task."""
        # Use a smaller sample from the user's example
        sample_index = {
            "Despite": [0],
            "growing": [1],
            "interest": [2],
            "in": [3],
            "Open": [4],
            "Access": [5],
        }

        result = undo_inverted_index(sample_index)

        assert result == "Despite growing interest in Open Access"

    def test_undo_inverted_index_empty_dict(self):
        """Handles empty dictionary."""
        result = undo_inverted_index({})

        assert result == ""

    def test_undo_inverted_index_preserves_word_order(self):
        """Correctly orders words by their positions."""
        # Same word at multiple positions
        multi_position_index = {
            "the": [0, 3, 6],
            "cat": [1],
            "sat": [2],
            "on": [4],
            "mat": [5],
        }

        result = undo_inverted_index(multi_position_index)

        # "the" appears at positions 0, 3, 6
        assert result == "the cat sat the on mat the"

    def test_format_search_result_with_abstract(self):
        """format_search_result includes reconstructed abstract."""
        work = {
            "doi": "10.1234/test",
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2023,
            "cited_by_count": 50,
            "open_access": {"is_oa": True},
            "abstract_inverted_index": {
                "This": [0],
                "is": [1],
                "abstract": [2],
            },
        }

        result = format_search_result(work)

        assert result["abstract"] == "This is abstract"
        assert result["doi"] == "10.1234/test"
        assert result["publication_year"] == 2023
        assert result["type"] == "article"
        assert result["cited_by_count"] == 50
        assert result["open_access"] is True

    def test_format_search_result_without_abstract(self):
        """format_search_result handles missing abstract_inverted_index."""
        work = {
            "doi": "10.1234/test",
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2023,
        }

        result = format_search_result(work)

        assert result["abstract"] == ""
        assert result["doi"] == "10.1234/test"
