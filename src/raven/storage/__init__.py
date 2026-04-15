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
- __init__.py: Re-exports for backward compatibility
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

# Re-export from submodules for backward compatibility
from raven.storage.db import (
    _load_vector_extension,
    _safe_add_column,
    init_database,
    serialize_f32,
)
from raven.storage.embedding import (
    add_embedding,
    get_embedding_exists,
    search_by_embedding,
)
from raven.storage.identifier import extract_identifier
from raven.storage.paper import (
    add_paper,
    get_paper_id_by_doi,
    get_paper_id_by_identifier,
    search_papers,
    update_paper,
)
