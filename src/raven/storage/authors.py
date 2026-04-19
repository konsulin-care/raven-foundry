"""Author entity operations for Raven storage.

Handles author schema with normalized authors table.
"""

import contextlib
import logging
import sqlite3
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def add_author(
    db_path: Path, author_id: str, name: str, orcid: str | None = None
) -> None:
    """Add or update an author in the authors table.

    Args:
        db_path: Path to the SQLite database file.
        author_id: OpenAlex author ID.
        name: Author's display name.
        orcid: ORCID identifier (optional).
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO authors (id, orcid, name)
            VALUES (?, ?, ?)
            """,
            (author_id, orcid, name),
        )
        conn.commit()


def convert_authors_to_data(
    authors: str | None,
) -> list[dict[str, Any]] | None:
    """Convert comma-separated authors string to structured data.

    Args:
        authors: Comma-separated author names string.

    Returns:
        List of author dicts with id, name, orcid, is_corresponding, order.
    """
    if not authors:
        return None

    author_names = [n.strip() for n in authors.split(",") if n.strip()]
    authors_data = []
    for idx, name in enumerate(author_names):
        normalized_name = name.lower().strip()
        author_id = "A" + str(uuid.uuid5(uuid.NAMESPACE_DNS, normalized_name))
        authors_data.append(
            {
                "id": author_id,
                "name": name,
                "orcid": None,
                "is_corresponding": 0,
                "order": idx,
            }
        )
    return authors_data
