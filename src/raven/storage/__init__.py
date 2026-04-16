"""Storage module - SQLite + vector storage for Raven.

Rules:
- Enforce DOI uniqueness
- Use WAL mode for durability
- Maintain indexes on DOI, type, title
- 384-dim embeddings with cosine similarity

Module Structure:
- db.py: Database initialization, schema, migrations
- paper.py: Paper CRUD operations
- embedding.py: Vector embedding storage and search
- __init__.py: Lazy re-exports for backward compatibility
"""

# Re-export for backward compatibility
__all__ = [
    # DB
    "_load_vector_extension",
    "_safe_add_column",
    "init_database",
    "serialize_f32",
    # Embedding
    "add_embedding",
    "get_embedding_exists",
    "search_by_embedding",
    # Identifier
    "extract_identifier",
    # Paper
    "add_paper",
    "get_paper_id_by_doi",
    "get_paper_id_by_identifier",
    "search_papers",
    "update_paper",
]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Type checking imports - loaded eagerly for type inference
    from raven.storage.db import (
        _load_vector_extension,
        init_database,
        serialize_f32,
    )
    from raven.storage.embedding import (
        add_embedding,
        get_embedding_exists,
        search_by_embedding,
    )
    from raven.storage.identifier import extract_identifier
    from raven.storage.migrations import _safe_add_column
    from raven.storage.paper import (
        add_paper,
        get_paper_id_by_doi,
        get_paper_id_by_identifier,
        search_papers,
        update_paper,
    )


def __getattr__(name: str) -> object:
    """Lazy loading for backward compatibility."""
    if name == "init_database":
        from raven.storage.db import init_database

        return init_database
    if name == "serialize_f32":
        from raven.storage.db import serialize_f32

        return serialize_f32
    if name == "_safe_add_column":
        from raven.storage.migrations import _safe_add_column

        return _safe_add_column
    if name == "_load_vector_extension":
        from raven.storage.db import _load_vector_extension

        return _load_vector_extension
    if name == "add_embedding":
        from raven.storage.embedding import add_embedding

        return add_embedding
    if name == "get_embedding_exists":
        from raven.storage.embedding import get_embedding_exists

        return get_embedding_exists
    if name == "search_by_embedding":
        from raven.storage.embedding import search_by_embedding

        return search_by_embedding
    if name == "add_paper":
        from raven.storage.paper import add_paper

        return add_paper
    if name == "get_paper_id_by_doi":
        from raven.storage.paper import get_paper_id_by_doi

        return get_paper_id_by_doi
    if name == "get_paper_id_by_identifier":
        from raven.storage.paper import get_paper_id_by_identifier

        return get_paper_id_by_identifier
    if name == "search_papers":
        from raven.storage.paper import search_papers

        return search_papers
    if name == "update_paper":
        from raven.storage.paper import update_paper

        return update_paper
    if name == "extract_identifier":
        from raven.storage.identifier import extract_identifier

        return extract_identifier
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
