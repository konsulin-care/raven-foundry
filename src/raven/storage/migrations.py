"""Database migrations for Raven storage.

Handles schema migrations and backward compatibility.
"""

import hashlib
import logging
import sqlite3

logger = logging.getLogger(__name__)

# Migration SQL constant
_DROP_AUTHORS_COLUMN_SQL = "ALTER TABLE papers DROP COLUMN authors"


def safe_add_column(conn: sqlite3.Connection, col_name: str, col_type: str) -> None:
    """Safely add a column with validation and quoting.

    This helper combines whitelist validation with identifier quoting to
    provide defense-in-depth against SQL injection in DDL statements.

    Args:
        conn: SQLite connection.
        col_name: Column name to add.
        col_type: SQL type (e.g., "TEXT", "INTEGER").

    Raises:
        ValueError: If column name is not in whitelist.
    """
    # Whitelist of valid column names for migration
    valid_column_names = frozenset(
        {
            "authors",
            "abstract",
            "year",
            "source",
            "identifier",
            "type",
            "ingested_at",
        }
    )

    # Validate against whitelist
    if col_name not in valid_column_names:
        raise ValueError(f"Invalid column name in migration: {col_name}")

    # Execute with quoted identifier to prevent SQL injection
    conn.execute(f"ALTER TABLE papers ADD COLUMN [{col_name}] {col_type}")


def _migrate_authors_to_normalized(conn: sqlite3.Connection) -> None:
    """Migrate legacy TEXT authors column to normalized schema.

    This migration:
    1. Parses comma-separated author names from legacy 'authors' column
    2. Inserts into 'authors' table (with generated ID, null orcid)
    3. Creates junction entries in 'paper_authors'
    4. Drops legacy 'authors' column from papers table

    Args:
        conn: SQLite connection.
    """
    # Check if papers table has the legacy authors column with data
    columns_result = conn.execute("PRAGMA table_info('papers')").fetchall()
    paper_columns = {row[1] for row in columns_result}

    if "authors" not in paper_columns:
        return  # No legacy column to migrate

    # Check if there's any data in the authors column
    has_data = conn.execute(
        "SELECT COUNT(*) FROM papers WHERE authors IS NOT NULL AND authors != ''"
    ).fetchone()[0]

    if has_data == 0:
        # No data, just drop the column
        try:
            conn.execute(_DROP_AUTHORS_COLUMN_SQL)
        except sqlite3.OperationalError:
            # SQLite 3.35.0+ required for DROP COLUMN
            pass
        return

    # Migration flag: track if we've already migrated
    migration_done = conn.execute("SELECT COUNT(*) FROM paper_authors").fetchone()[0]

    if migration_done > 0:
        # Already migrated, drop legacy column
        try:
            conn.execute(_DROP_AUTHORS_COLUMN_SQL)
        except sqlite3.OperationalError:
            pass
        return

    # Perform migration: parse comma-separated authors
    papers_with_authors = conn.execute("""
        SELECT id, authors FROM papers
        WHERE authors IS NOT NULL AND authors != ''
        """).fetchall()

    for paper_id, authors_text in papers_with_authors:
        # Parse comma-separated author names
        author_names = [n.strip() for n in authors_text.split(",") if n.strip()]

        for order, name in enumerate(author_names):
            author_id = "A" + hashlib.sha256(name.encode()).hexdigest()[:10].upper()

            # Insert into authors table
            conn.execute(
                """
                INSERT OR IGNORE INTO authors (id, orcid, name)
                VALUES (?, NULL, ?)
                """,
                (author_id, name),
            )

            # Insert into junction table
            conn.execute(
                """
                INSERT INTO paper_authors (paper_id, author_id, author_order, is_corresponding)
                VALUES (?, ?, ?, 0)
                """,
                (paper_id, author_id, order),
            )

    # Drop legacy authors column
    try:
        conn.execute(_DROP_AUTHORS_COLUMN_SQL)
    except sqlite3.OperationalError:
        pass
