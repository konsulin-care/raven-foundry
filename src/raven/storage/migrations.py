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
    Real error messages include: 'near "DROP": syntax error' or similar
    patterns containing both 'drop' and 'syntax error'.

    Args:
        e: The OperationalError to check.

    Returns:
        True if this is the expected unsupported operation error.
    """
    msg = str(e).lower()
    return "drop column" in msg or ("drop" in msg and "syntax error" in msg)


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


def _drop_authors_column_safe(
    conn: sqlite3.Connection, commit_on_success: bool = False
) -> None:
    """Safely drop the legacy authors column with error handling.

    Handles SQLite versions < 3.35.0 that don't support DROP COLUMN.

    Args:
        conn: SQLite connection.
        commit_on_success: Whether to commit after successful drop.
    """
    try:
        conn.execute(_DROP_AUTHORS_COLUMN_SQL)
    except sqlite3.OperationalError as e:
        if _is_unsupported_drop_column_error(e):
            if commit_on_success:
                conn.commit()
            return
        logger.warning("DROP COLUMN failed: %s", e)
        raise
    if commit_on_success:
        conn.commit()


def _insert_author_for_paper(
    conn: sqlite3.Connection, paper_id: int, author_name: str, order: int
) -> None:
    """Insert a single author's normalized entry with collision detection.

    Generates deterministic UUID5 from normalized name, detects collisions,
    inserts into authors and paper_authors junction tables.

    Args:
        conn: SQLite connection.
        paper_id: The paper ID to link the author to.
        author_name: The author's display name.
        author_order: The order index for this author on the paper.
    """
    normalized_name = author_name.lower().strip()
    author_id = "A" + str(uuid.uuid5(uuid.NAMESPACE_DNS, normalized_name))

    existing = conn.execute(
        "SELECT name FROM authors WHERE id = ?", (author_id,)
    ).fetchone()
    if existing and existing[0] != author_name:
        raise RuntimeError(
            f"Author ID collision: {author_id} maps to '{existing[0]}' "
            f"but trying to insert '{author_name}'. Manual intervention required."
        )

    conn.execute(
        "INSERT OR IGNORE INTO authors (id, orcid, name) VALUES (?, NULL, ?)",
        (author_id, author_name),
    )
    conn.execute(
        "INSERT INTO paper_authors (paper_id, author_id, author_order, is_corresponding) "
        "VALUES (?, ?, ?, 0)",
        (paper_id, author_id, order),
    )


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
    columns_result = conn.execute("PRAGMA table_info('papers')").fetchall()
    paper_columns = {row[1] for row in columns_result}

    if "authors" not in paper_columns:
        return

    has_data = conn.execute(
        "SELECT COUNT(*) FROM papers WHERE authors IS NOT NULL AND authors != ''"
    ).fetchone()[0]

    if has_data == 0:
        _drop_authors_column_safe(conn)
        return

    migration_done = conn.execute("SELECT COUNT(*) FROM paper_authors").fetchone()[0]

    if migration_done > 0:
        _drop_authors_column_safe(conn)
        return

    conn.execute("BEGIN")

    try:
        papers_with_authors = conn.execute("""
            SELECT id, authors FROM papers
            WHERE authors IS NOT NULL AND authors != ''
            """).fetchall()

        for paper_id, authors_text in papers_with_authors:
            author_names = [n.strip() for n in authors_text.split(",") if n.strip()]

            for order, name in enumerate(author_names):
                _insert_author_for_paper(conn, paper_id, name, order)

        _drop_authors_column_safe(conn, commit_on_success=True)
    except Exception:
        conn.rollback()
        raise
