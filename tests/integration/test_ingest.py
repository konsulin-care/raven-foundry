"""Integration tests for CLI ingest commands.

Run with: pytest tests/integration/test_ingest.py -v
"""

from unittest.mock import patch

from click.testing import CliRunner

import raven.main


class TestCLIIngest:
    """Tests for raven ingest CLI command."""

    def test_success(self, tmp_path, monkeypatch):
        """Test 'raven ingest' with successful API response."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("RAVEN_DATA_DIR", str(tmp_path))
        mock_result = {
            "identifier": "doi:10.1234/test",
            "title": "Test Research Paper",
            "type": "article",
        }
        with patch("raven.cli.resolver.resolve_db_path", return_value=db_path):
            with patch("raven.cli.ingest.ingest_paper", lambda db, doi: mock_result):
                result = runner.invoke(
                    raven.main.cli, ["ingest", "10.1234/test", "--db", str(db_path)]
                )
                assert result.exit_code == 0
                assert "Ingesting: 10.1234/test" in result.output
                assert "Successfully ingested: Test Research Paper" in result.output

    def test_failure(self, tmp_path, monkeypatch):
        """Test 'raven ingest' when API returns failure."""
        runner = CliRunner()
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("RAVEN_DATA_DIR", str(tmp_path))
        with patch("raven.cli.resolver.resolve_db_path", return_value=db_path):
            with patch("raven.cli.ingest.ingest_paper", lambda db, identifier: None):
                result = runner.invoke(
                    raven.main.cli, ["ingest", "10.9999/failure", "--db", str(db_path)]
                )
                assert result.exit_code == 0
                assert "Ingesting: 10.9999/failure" in result.output
                assert "Failed to ingest publication" in result.output
