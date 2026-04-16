"""Unit tests for main.py functions.

Run with: pytest tests/unit/test_main.py -v
"""

from unittest.mock import patch


class TestMainFunctions:
    """Tests for main.py utility functions."""

    def test_get_version_from_metadata(self):
        """Verify _get_version returns version from metadata."""
        with patch("importlib.metadata.version") as mock_version:
            mock_version.return_value = "1.2.3"

            from raven.main import _get_version

            result = _get_version()

            assert result == "1.2.3"

    def test_get_version_fallback(self):
        """Verify _get_version falls back to dev on error."""
        with patch("importlib.metadata.version", side_effect=Exception("fail")):
            import raven.main

            # Need to reload to clear any cached version
            with patch("importlib.metadata.version", side_effect=Exception("fail")):
                result = raven.main._get_version()

            assert result == "dev"

    def test_resolve_db_path_explicit(self, tmp_path):
        """Verify explicit --db path takes precedence."""
        from raven.main import _resolve_db_path

        explicit_path = tmp_path / "custom.db"
        result = _resolve_db_path(db_path=explicit_path)

        assert result == explicit_path

    def test_resolve_db_path_from_env(self, tmp_path, monkeypatch):
        """Verify db path derived from RAVEN_DATA_DIR."""
        # Set up temp env file
        env_file = tmp_path / ".env"
        test_data_dir = tmp_path / "raven_data"
        test_data_dir.mkdir()
        env_file.write_text(f"RAVEN_DATA_DIR={test_data_dir}\n")

        from raven.main import _resolve_db_path

        result = _resolve_db_path(env_path=env_file)

        assert str(result).endswith("raven.db")
        assert str(result).startswith(str(test_data_dir))

    def test_resolve_db_path_default(self, monkeypatch):
        """Verify default db path when no env file."""
        # Ensure no RAVEN_DATA_DIR is set
        monkeypatch.delenv("RAVEN_DATA_DIR", raising=False)
        # Block .env loading
        from unittest.mock import patch as mock_patch

        with mock_patch("raven.paths.find_env_file", return_value=None):
            from raven.main import _resolve_db_path

            result = _resolve_db_path(env_path=None)

            # Should use default data dir
            assert "raven.db" in str(result)
