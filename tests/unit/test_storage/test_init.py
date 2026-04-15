"""Unit tests for init_database function.

Run with: pytest tests/unit/test_storage/test_init.py -v
"""

import sqlite3

from raven.storage import init_database


class TestInitDatabase:
    """Tests for init_database function."""

    def test_init_database_runs_without_error(self, tmp_path, mocker):
        """init_database executes without raising exceptions."""
        db_path = tmp_path / "test.db"

        # Mock the vector extension loader to avoid requiring native extension in tests
        mocker.patch("raven.storage._load_vector_extension")
        init_database(db_path)

    def test_init_database_creates_db_file(self, tmp_path, mocker):
        """init_database creates the database file."""
        db_path = tmp_path / "test.db"

        # Mock the vector extension loader to avoid requiring native extension in tests
        mocker.patch("raven.storage._load_vector_extension")
        init_database(db_path)

        # Database file should exist
        assert db_path.exists()

    def test_init_database_creates_valid_columns(self, tmp_path, mocker):
        """init_database creates tables with expected columns."""
        db_path = tmp_path / "test.db"

        # Mock the vector extension loader
        mocker.patch("raven.storage._load_vector_extension")
        init_database(db_path)

        # Verify expected columns exist
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(papers)")
            columns = {row[1] for row in cursor.fetchall()}

        expected_columns = {
            "id",
            "identifier",
            "title",
            "authors",
            "abstract",
            "publication_year",
            "venue",
            "type",
            "created_at",
            "openalex_id",
        }
        assert expected_columns.issubset(columns)
