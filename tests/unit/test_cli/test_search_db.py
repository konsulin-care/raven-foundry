"""Unit tests for search_db helpers.

Run with: pytest tests/unit/test_cli/test_search_db.py -v
"""

import sqlite3
from unittest.mock import patch

from raven.cli.search_db import check_batch_ingested


class TestCheckBatchIngested:
    """Tests for check_batch_ingested function."""

    def test_returns_empty_set_when_no_identifiers(self, tmp_path):
        """Verify empty set is returned when no identifiers in results."""
        db_path = tmp_path / "test.db"
        results = []

        result = check_batch_ingested(db_path, results)

        assert result == set()

    def test_returns_empty_set_when_missing_db(self, tmp_path):
        """Verify empty set is returned when DB file doesn't exist."""
        db_path = tmp_path / "nonexistent.db"
        results = [{"identifier": "doi:10.1234/test"}]

        result = check_batch_ingested(db_path, results)

        assert result == set()

    def test_returns_empty_set_when_papers_table_missing(self, tmp_path):
        """Verify empty set is returned when papers table doesn't exist."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS other_table (id INTEGER)")

        results = [{"identifier": "doi:10.1234/test"}]

        result = check_batch_ingested(db_path, results)

        assert result == set()

    def test_returns_matching_identifiers(self, tmp_path):
        """Verify matching identifiers are returned."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY,
                    identifier TEXT COLLATE NOCASE,
                    title TEXT
                )
            """)
            conn.execute(
                "INSERT INTO papers (identifier, title) VALUES (?, ?)",
                ("doi:10.1234/test", "Test Paper"),
            )

        results = [
            {"identifier": "doi:10.1234/test"},
            {"identifier": "doi:10.5678/other"},
        ]

        result = check_batch_ingested(db_path, results)

        assert result == {"doi:10.1234/test"}

    def test_returns_empty_set_on_operational_error(self, tmp_path):
        """Verify empty set is returned on sqlite3.OperationalError."""
        db_path = tmp_path / "test.db"

        with patch("raven.cli.search_db.sqlite3.connect") as mock_connect:
            mock_connect.side_effect = sqlite3.OperationalError("locked")

            results = [{"identifier": "doi:10.1234/test"}]

            result = check_batch_ingested(db_path, results)

            assert result == set()

    def test_returns_empty_set_on_oserror(self, tmp_path):
        """Verify empty set is returned on OSError (e.g., permission denied)."""
        db_path = tmp_path / "test.db"
        db_path.touch()

        with patch("raven.cli.search_db.sqlite3.connect") as mock_connect:
            mock_connect.side_effect = OSError("Permission denied")

            results = [{"identifier": "doi:10.1234/test"}]

            result = check_batch_ingested(db_path, results)

            assert result == set()

    def test_case_insensitive_identifier_matching(self, tmp_path):
        """Verify identifier matching is case-insensitive."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY,
                    identifier TEXT COLLATE NOCASE,
                    title TEXT
                )
            """)
            conn.execute(
                "INSERT INTO papers (identifier, title) VALUES (?, ?)",
                ("DOI:10.1234/TEST", "Test Paper"),
            )

        results = [{"identifier": "doi:10.1234/test"}]

        result = check_batch_ingested(db_path, results)

        assert result == {"doi:10.1234/test"}
