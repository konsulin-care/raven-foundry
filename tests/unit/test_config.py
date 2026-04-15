"""Unit tests for Raven config module.

Run with: pytest tests/unit/test_config.py -v
"""

from unittest.mock import patch

import pytest

import raven.config
from raven.config import (
    get_groq_api_key,
    get_openalex_api_key,
    get_openalex_api_url,
)

# Config Module Tests


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

    def test_get_data_dir_with_xdghome(self, monkeypatch):
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
