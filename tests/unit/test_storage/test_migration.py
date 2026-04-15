"""Unit tests for doi->identifier schema migration.

Run with: pytest tests/unit/test_storage/test_migration.py -v
"""

import sqlite3

from raven.storage import init_database


class TestDoiToIdentifierMigration:
    """Tests for doi->identifier schema migration.

    This tests the fix for the bug where the migration logic captured
    existing_columns AFTER adding new columns, causing the doi migration
    to fail silently and leave a NOT NULL constraint on the old doi column.
    """

    def test_migration_with_old_doi_column(self, tmp_path):
        """init_database migrates old doi column to identifier correctly.

        Simulates a database with the old schema (doi column) and verifies
        that init_database() properly migrates data to the new identifier column
        and drops the old doi column.
        """
        db_path = tmp_path / "test.db"

        # Create database with old schema (has doi column with NOT NULL constraint)
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY,
                doi TEXT NOT NULL,
                title TEXT NOT NULL
            )
        """)
        # Insert test data
        conn.execute(
            "INSERT INTO papers (doi, title) VALUES (?, ?)",
            ("10.1234/test", "Test Paper"),
        )
        conn.commit()
        conn.close()

        # Run init_database to trigger migration
        init_database(db_path)

        # Verify: doi column should be dropped, identifier should have data
        conn = sqlite3.connect(db_path)
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(papers)").fetchall()
        }

        assert "doi" not in columns, "doi column should be dropped after migration"
        assert "identifier" in columns, "identifier column should exist"

        # Verify data was migrated
        result = conn.execute("SELECT identifier FROM papers WHERE id = 1").fetchone()
        assert result is not None
        assert result[0] == "doi:10.1234/test", (
            "DOI should be migrated with doi: prefix"
        )

        conn.close()

    def test_migration_idempotent_no_doi_column(self, tmp_path):
        """init_database handles database without doi column correctly.

        Verifies that databases without the old doi column don't trigger
        the migration and work correctly.
        """
        db_path = tmp_path / "test.db"

        # Run init_database on fresh database
        init_database(db_path)

        # Verify: identifier column exists, no doi column
        conn = sqlite3.connect(db_path)
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(papers)").fetchall()
        }

        assert "identifier" in columns
        assert "doi" not in columns

        conn.close()

    def test_migration_with_null_doi_values(self, tmp_path):
        """init_database handles NULL doi values during migration."""
        db_path = tmp_path / "test.db"

        # Create database with old schema and NULL doi values
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY,
                doi TEXT,
                title TEXT NOT NULL
            )
        """)
        # Insert record with NULL doi
        conn.execute(
            "INSERT INTO papers (doi, title) VALUES (NULL, ?)", ("No DOI Paper",)
        )
        conn.commit()
        conn.close()

        # Run init_database to trigger migration
        init_database(db_path)

        # Verify: record with NULL doi should have empty/null identifier
        conn = sqlite3.connect(db_path)
        result = conn.execute("SELECT identifier FROM papers WHERE id = 1").fetchone()
        # NULL doi values are skipped in migration (WHERE doi IS NOT NULL AND doi != '')
        assert result[0] is None or result[0] == ""

        conn.close()
