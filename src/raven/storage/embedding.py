"""Vector embedding storage and search for Raven.

Rules:
- Maintain 384-dim embeddings
- Use cosine similarity for vector search
"""

import contextlib
import json
import logging
import sqlite3
from pathlib import Path
from typing import Any

from raven.storage.db import _load_vector_extension

logger = logging.getLogger(__name__)

# Embedding dimension as per AGENTS.md
EMBEDDING_DIMENSION = 384


def get_embedding_exists(db_path: Path, paper_id: int) -> bool:
    """Check if embedding exists for a paper.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper to check.

    Returns:
        True if embedding exists, False otherwise.
    """
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.execute(
            "SELECT 1 FROM embeddings WHERE paper_id = ?",
            (paper_id,),
        )
        return cursor.fetchone() is not None


def add_embedding(
    db_path: Path,
    paper_id: int,
    embedding: list[float],
    text: str,
    content_type: str,
) -> None:
    """Add vector embedding for a paper.

    Args:
        db_path: Path to the SQLite database file.
        paper_id: ID of the paper to associate the embedding with.
        embedding: 384-dimensional embedding vector.
        text: Original text being embedded.
        content_type: Type of text (one of: title, abstract, abstract chunk, full text summary, section summary, section chunk).

    Raises:
        ValueError: If the embedding vector length doesn't match expected dimension.
    """
    if len(embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(embedding)}"
        )

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        # Load sqliteai-vector extension
        _load_vector_extension(conn)

        # Initialize vector column (required for each new connection)
        conn.execute(
            "SELECT vector_init('embeddings', 'embedding', "
            "'type=FLOAT32,dimension=384,distance=COSINE')"
        )

        # Insert embedding using vector_as_f32 for proper formatting
        embedding_json = json.dumps(embedding)
        conn.execute(
            "INSERT OR REPLACE INTO embeddings (paper_id, embedding, text, type) VALUES (?, vector_as_f32(?), ?, ?)",
            (paper_id, embedding_json, text, content_type),
        )
        conn.commit()


def search_by_embedding(
    db_path: Path,
    query_embedding: list[float],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Search papers by vector similarity (KNN).

    Args:
        db_path: Path to the SQLite database file.
        query_embedding: 384-dimensional query embedding vector.
        top_k: Number of nearest neighbors to return (default: 10).

    Returns:
        List of paper records with distance scores, sorted by distance ascending.
        Returns all top_k results - filtering by max_distance should be done
        in the calling code.

    Raises:
        ValueError: If the query embedding dimension doesn't match expected dimension.
    """
    if len(query_embedding) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Query embedding dimension mismatch: expected {EMBEDDING_DIMENSION}, got {len(query_embedding)}"
        )

    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        # Load sqliteai-vector extension
        _load_vector_extension(conn)

        # Initialize vector column (required for each new connection)
        conn.execute(
            "SELECT vector_init('embeddings', 'embedding', "
            "'type=FLOAT32,dimension=384,distance=COSINE')"
        )

        # Serialize query and run KNN search using vector_full_scan in top-k mode
        query_json = json.dumps(query_embedding)
        conn.row_factory = sqlite3.Row

        # Check if normalized author tables exist
        tables = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = {t[0] for t in tables}

        # Use top-k mode - returns sorted results by distance
        # Authors are fetched from normalized schema or legacy column
        if "authors" in table_names and "paper_authors" in table_names:
            cursor = conn.execute(
                """
                SELECT
                    p.id,
                    p.identifier,
                    p.title,
                    p.abstract,
                    p.year,
                    p.source,
                    p.type,
                    p.ingested_at,
                    e.text,
                    e.type AS embedding_type,
                    (
                        SELECT GROUP_CONCAT(a.name, ', ')
                        FROM paper_authors pa
                        JOIN authors a ON pa.author_id = a.id
                        WHERE pa.paper_id = p.id
                        ORDER BY pa.author_order
                    ) AS authors,
                    v.distance
                FROM embeddings e
                JOIN papers p ON e.paper_id = p.id
                JOIN vector_full_scan('embeddings', 'embedding', vector_as_f32(?), ?) AS v
                ON e.paper_id = v.rowid
                ORDER BY v.distance
            """,
                (query_json, top_k),
            )
        else:
            # Fallback to legacy authors column
            cursor = conn.execute(
                """
                SELECT
                    p.id,
                    p.identifier,
                    p.title,
                    p.authors,
                    p.abstract,
                    p.year,
                    p.source,
                    p.type,
                    p.ingested_at,
                    e.text,
                    e.type AS embedding_type,
                    v.distance
                FROM embeddings e
                JOIN papers p ON e.paper_id = p.id
                JOIN vector_full_scan('embeddings', 'embedding', vector_as_f32(?), ?) AS v
                ON e.paper_id = v.rowid
                ORDER BY v.distance
            """,
                (query_json, top_k),
            )

        results = [dict(row) for row in cursor.fetchall()]

    return results
