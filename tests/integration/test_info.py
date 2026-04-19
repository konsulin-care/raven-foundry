"""Integration tests for CLI info commands.

Run with: pytest tests/integration/test_info.py -v
"""

import sqlite3
import unittest.mock as mock

from click.testing import CliRunner

import raven.main
import raven.paths
from raven.storage import add_paper, init_database


class TestCLIInfo:
    """Tests for raven info CLI command."""

    def test_no_database(self, tmp_path, monkeypatch):
        """Test 'raven info' when no database exists."""
        runner = CliRunner()
        db_path = tmp_path / "nonexistent.db"
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)
        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "Version:" in result.output
        assert "Total papers indexed: 0" in result.output

    def test_with_papers(self, tmp_path, monkeypatch):
        """Test 'raven info' with papers in database."""
        runner = CliRunner()
        db_path = tmp_path / "raven.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "Test Paper", "article")
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)
        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "Total papers indexed: 1" in result.output

    def test_db_exists_but_no_papers_table(self, tmp_path, monkeypatch):
        """Test 'raven info' when DB exists but lacks papers table."""
        runner = CliRunner()
        db_path = tmp_path / "raven.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS metadata (key TEXT, value TEXT)")
            conn.commit()
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)
        result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])
        assert result.exit_code == 0
        assert "'papers' table not found" in result.output
        assert "Total papers indexed: 0" in result.output

    def test_operational_error_re_raised(self, tmp_path, monkeypatch):
        """Test 'raven info' re-raises OperationalError."""
        runner = CliRunner()
        db_path = tmp_path / "raven.db"
        db_path.touch()
        monkeypatch.setattr(raven.paths, "get_data_dir", lambda: tmp_path)

        class MockConn:
            def __init__(self, error_msg):
                self.error_msg = error_msg

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def execute(self, sql, *args, **kwargs):
                raise sqlite3.OperationalError(self.error_msg)

        def create_mock_conn(path, **kwargs):
            return MockConn("database is locked")

        with mock.patch("raven.cli.info.sqlite3.connect", side_effect=create_mock_conn):
            result = runner.invoke(raven.main.cli, ["info", "--db", str(db_path)])
        assert result.exit_code == 1
        assert result.exception is not None
        assert isinstance(result.exception, sqlite3.OperationalError)
        assert "database is locked" in str(result.exception)
