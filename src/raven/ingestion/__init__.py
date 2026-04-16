"""Ingestion module - OpenAlex API + PDF processing for Raven.

Environment (from .env):
- OPENALEX_API_KEY: Required. Get from https://openalex.org/
- OPENALEX_API_URL: Optional. Defaults to https://api.openalex.org

Responsibilities:
- Query OpenAlex API
- Download PDFs
- Convert PDF → Markdown (MarkItDown)
- Clean extracted text

Identifier Support:
- DOI: 10.5281/zenodo.18201069, doi:10.5281/zenodo.18201069
- OpenAlex ID: W7119934875, openalex:W7119934875
- PMID: 29456894, pmid:29456894
- PMCID: PMC1234567, pmcid:PMC1234567
- MAG: 2741809807, mag:2741809807

Rules:
- Deduplicate using identifier before insertion
- Do not use LLMs in this module
- Keep processing CPU-efficient
- Ensure ingestion integrates cleanly with CLI workflow

Module Structure:
- api.py: OpenAlex API client base (fetch)
- search.py: Search operations (semantic, keyword, hybrid)
- search_client.py: Shared search client utilities
- metadata.py: Metadata extraction from OpenAlex results
- identifier.py: DOI/normalization utilities
- text.py: Abstract reconstruction, result formatting
- pipeline.py: Ingestion orchestration (ingest_paper, ingest_search_results)
- bibtex.py: BibTeX parsing
- bibtex_normalize.py: BibTeX identifier normalization
- constants.py: Shared constants (filters, sort orders)
- __init__.py: Lazy re-exports for backward compatibility
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

# Re-export for backward compatibility
__all__ = [
    # Config
    "get_openalex_api_key",
    "get_openalex_api_url",
    # Embeddings
    "generate_embedding",
    "generate_embeddings_batch",
    # Ingestion API
    "DEFAULT_FILTERS",
    "DEFAULT_SORT_ORDER",
    "SEMANTIC_FILTERS",
    "_create_session_with_retries",
    "_get_openalex_base_url",
    "fetch_work",
    # Identifier
    "normalize_doi",
    "normalize_identifier",
    # Metadata
    "prepare_paper_info",
    # Pipeline
    "_get_existing_paper_info",
    "_handle_existing_paper",
    "ingest_paper",
    "ingest_search_results",
    # Search
    "search_works",
    "search_works_semantic",
    "search_works_keyword",
    # Text
    "combine_title_abstract",
    "format_search_result",
    "undo_inverted_index",
    # Storage
    "add_embedding",
    "add_paper",
    "get_embedding_exists",
    "get_paper_id_by_identifier",
    "update_paper",
    # Logger
    "logger",
]

# Re-export logger for backward compatibility
logger = logging.getLogger(__name__)

# Module path constants to avoid duplication
_MODULE_INGESTION_API = "raven.ingestion.api"
_MODULE_INGESTION_PIPELINE = "raven.ingestion.pipeline"
_MODULE_INGESTION_TEXT = "raven.ingestion.text"
_MODULE_STORAGE = "raven.storage"

# Lazy loading mapping for backward compatibility
_LAZY_IMPORTS = {
    # Config
    "get_openalex_api_key": ("raven.config", "get_openalex_api_key"),
    "get_openalex_api_url": ("raven.config", "get_openalex_api_url"),
    # Embeddings
    "generate_embedding": ("raven.embeddings", "generate_embedding"),
    "generate_embeddings_batch": ("raven.embeddings", "generate_embeddings_batch"),
    # Ingestion API
    "DEFAULT_FILTERS": (_MODULE_INGESTION_API, "DEFAULT_FILTERS"),
    "DEFAULT_SORT_ORDER": (_MODULE_INGESTION_API, "DEFAULT_SORT_ORDER"),
    "SEMANTIC_FILTERS": (_MODULE_INGESTION_API, "SEMANTIC_FILTERS"),
    "_create_session_with_retries": (
        _MODULE_INGESTION_API,
        "_create_session_with_retries",
    ),
    "_get_openalex_base_url": (_MODULE_INGESTION_API, "_get_openalex_base_url"),
    "fetch_work": (_MODULE_INGESTION_API, "fetch_work"),
    # Identifier
    "normalize_doi": ("raven.ingestion.identifier", "normalize_doi"),
    "normalize_identifier": ("raven.ingestion.identifier", "normalize_identifier"),
    # Metadata
    "prepare_paper_info": ("raven.ingestion.metadata", "prepare_paper_info"),
    # Pipeline
    "_get_existing_paper_info": (
        _MODULE_INGESTION_PIPELINE,
        "_get_existing_paper_info",
    ),
    "_handle_existing_paper": (_MODULE_INGESTION_PIPELINE, "_handle_existing_paper"),
    "ingest_paper": (_MODULE_INGESTION_PIPELINE, "ingest_paper"),
    "ingest_search_results": (_MODULE_INGESTION_PIPELINE, "ingest_search_results"),
    # Search
    "search_works": ("raven.ingestion.search", "search_works"),
    "search_works_semantic": ("raven.ingestion.search", "search_works_semantic"),
    "search_works_keyword": ("raven.ingestion.search_keyword", "search_works_keyword"),
    # Text
    "combine_title_abstract": (_MODULE_INGESTION_TEXT, "combine_title_abstract"),
    "format_search_result": (_MODULE_INGESTION_TEXT, "format_search_result"),
    "undo_inverted_index": (_MODULE_INGESTION_TEXT, "undo_inverted_index"),
    # Storage
    "add_embedding": (_MODULE_STORAGE, "add_embedding"),
    "add_paper": (_MODULE_STORAGE, "add_paper"),
    "get_embedding_exists": (_MODULE_STORAGE, "get_embedding_exists"),
    "get_paper_id_by_identifier": (_MODULE_STORAGE, "get_paper_id_by_identifier"),
    "update_paper": (_MODULE_STORAGE, "update_paper"),
}


def __getattr__(name: str) -> object:
    """Lazy loading for backward compatibility exports."""
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        import importlib

        module = importlib.import_module(module_path)
        return getattr(module, attr_name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    # Type hints for mypy - these are only checked at type-check time
    from raven.config import get_openalex_api_key, get_openalex_api_url
    from raven.embeddings import (
        generate_embedding,
        generate_embeddings_batch,
    )
    from raven.ingestion.api import (
        DEFAULT_FILTERS,
        DEFAULT_SORT_ORDER,
        SEMANTIC_FILTERS,
        _create_session_with_retries,
        _get_openalex_base_url,
        fetch_work,
    )
    from raven.ingestion.identifier import (
        normalize_doi,
        normalize_identifier,
    )
    from raven.ingestion.metadata import prepare_paper_info
    from raven.ingestion.pipeline import (
        _get_existing_paper_info,
        _handle_existing_paper,
        ingest_paper,
        ingest_search_results,
    )
    from raven.ingestion.search import (
        search_works,
        search_works_semantic,
    )
    from raven.ingestion.search_keyword import search_works_keyword
    from raven.ingestion.text import (
        combine_title_abstract,
        format_search_result,
        undo_inverted_index,
    )
    from raven.storage import (
        add_embedding,
        add_paper,
        get_embedding_exists,
        get_paper_id_by_identifier,
        update_paper,
    )
