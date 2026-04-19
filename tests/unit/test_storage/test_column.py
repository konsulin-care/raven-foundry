"""Unit tests for safe_add_column helper function."""

import sqlite3

import pytest

from raven.storage import safe_add_column


class TestSafeAddColumn:
    """Tests for safe_add_column helper function."""

    @pytest.fixture
    def conn(self, tmp_path):
        """Create test database with papers table."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            )
        """)
        conn.commit()
        yield conn
        conn.close()

    def test_safe_add_column_valid(self, conn):
        """safe_add_column adds valid column."""
        safe_add_column(conn, "authors", "TEXT")

        # Verify column was added
        cursor = conn.execute("PRAGMA table_info(papers)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "authors" in columns

    def test_safe_add_column_invalid_raises(self, conn):
        """safe_add_column raises for invalid column name."""
        with pytest.raises(ValueError, match="Invalid column name"):
            safe_add_column(conn, "malicious_column", "TEXT")

    def test_safe_add_column_abstract_type(self, conn):
        """safe_add_column handles abstract column type."""
        safe_add_column(conn, "abstract", "TEXT")

        cursor = conn.execute("PRAGMA table_info(papers)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "abstract" in columns
