"""Integration tests for CLI cache commands.

Run with: pytest tests/integration/test_cache.py -v
"""

from unittest.mock import patch

from click.testing import CliRunner

import raven.main
import raven.paths


class TestCLICache:
    """Tests for raven cache CLI commands."""

    def test_status_shows_info(self, tmp_path, monkeypatch):
        """Test 'raven cache status' shows cache info."""
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)
        runner = CliRunner()
        with patch("raven.cli.cache.get_model_cache_size") as mock_size:
            mock_size.return_value = 440401920  # ~420 MB
            result = runner.invoke(raven.main.cli, ["cache", "status"])
            assert result.exit_code == 0
            assert "Cache directory:" in result.output
            assert "Cache size:" in result.output

    def test_status_no_cache(self, tmp_path, monkeypatch):
        """Test 'raven cache status' when no cache exists."""
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)
        runner = CliRunner()
        with patch("raven.cli.cache.get_model_cache_size") as mock_size:
            mock_size.return_value = None
            result = runner.invoke(raven.main.cli, ["cache", "status"])
            assert result.exit_code == 0
            assert "No cache found" in result.output

    def test_clean_deletes_cache(self, tmp_path, monkeypatch):
        """Test 'raven cache clean' deletes cache."""
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)
        runner = CliRunner()
        with patch("raven.cli.cache.clean_model_cache") as mock_clean:
            result = runner.invoke(raven.main.cli, ["cache", "clean"])
            assert result.exit_code == 0
            assert "Cache cleaned successfully" in result.output
            mock_clean.assert_called_once()
