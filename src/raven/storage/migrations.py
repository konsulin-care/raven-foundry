"""Database migrations for Raven storage.

Handles schema migrations and backward compatibility.
"""

import logging
import sqlite3
import uuid

logger = logging.getLogger(__name__)

_DROP_AUTHORS_COLUMN_SQL = "ALTER TABLE papers DROP COLUMN authors"


def _is_unsupported_drop_column_error(e: sqlite3.OperationalError) -> bool:
    """Check if OperationalError is due to SQLite lacking DROP COLUMN support.

    SQLite versions < 3.35.0 do not support ALTER TABLE DROP COLUMN.
    The error message is: "no such command: DROP COLUMN"

    Args:
        e: The OperationalError to check.

    Returns:
        True if this is the expected unsupported operation error.
    """
    return "drop column" in str(e).lower()


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
        except sqlite3.OperationalError as e:
            if _is_unsupported_drop_column_error(e):
                return
            logger.warning("DROP COLUMN failed (no data case): %s", e)
            raise
        return

    # Migration flag: track if we've already migrated
    migration_done = conn.execute("SELECT COUNT(*) FROM paper_authors").fetchone()[0]

    if migration_done > 0:
        # Already migrated, drop legacy column
        try:
            conn.execute(_DROP_AUTHORS_COLUMN_SQL)
        except sqlite3.OperationalError as e:
            if _is_unsupported_drop_column_error(e):
                return
            logger.warning("DROP COLUMN failed (already migrated case): %s", e)
            raise
        return

    # Perform migration: parse comma-separated authors
    # Wrap in explicit transaction to ensure atomicity
    conn.execute("BEGIN")

    try:
        papers_with_authors = conn.execute("""
            SELECT id, authors FROM papers
            WHERE authors IS NOT NULL AND authors != ''
            """).fetchall()

        for paper_id, authors_text in papers_with_authors:
            # Parse comma-separated author names
            author_names = [n.strip() for n in authors_text.split(",") if n.strip()]

            for order, name in enumerate(author_names):
                # UUID5 provides 128-bit collision resistance; truncating SHA256
                # to 10 chars (~40 bits) risks silent merges under INSERT OR IGNORE.
                # Using namespaced UUID5 with normalized name for deterministic ID,
                # with collision check to catch any hash namespace collisions.
                normalized_name = name.lower().strip()
                author_id = "A" + str(uuid.uuid5(uuid.NAMESPACE_DNS, normalized_name))

                # Detect collisions: if author_id exists with different name, fail loudly
                existing = conn.execute(
                    "SELECT name FROM authors WHERE id = ?", (author_id,)
                ).fetchone()
                if existing and existing[0] != name:
                    raise RuntimeError(
                        f"Author ID collision: {author_id} maps to '{existing[0]}' "
                        f"but trying to insert '{name}'. Manual intervention required."
                    )

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
        except sqlite3.OperationalError as e:
            if _is_unsupported_drop_column_error(e):
                conn.commit()
                return
            logger.warning("DROP COLUMN failed (post-migration case): %s", e)
            conn.rollback()
            raise

        conn.commit()
    except Exception:
        conn.rollback()
        raise
