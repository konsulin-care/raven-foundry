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
- metadata.py: Metadata extraction from OpenAlex results
- identifier.py: DOI/normalization utilities
- text.py: Abstract reconstruction, result formatting
- pipeline.py: Ingestion orchestration (ingest_paper, ingest_search_results)
- bibtex.py: BibTeX parsing
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
    "_prepare_paper_info",
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


def __getattr__(name: str) -> object:
    """Lazy loading for backward compatibility exports."""
    # Config
    if name == "get_openalex_api_key":
        from raven.config import get_openalex_api_key

        return get_openalex_api_key
    if name == "get_openalex_api_url":
        from raven.config import get_openalex_api_url

        return get_openalex_api_url

    # Embeddings
    if name == "generate_embedding":
        from raven.embeddings import generate_embedding

        return generate_embedding
    if name == "generate_embeddings_batch":
        from raven.embeddings import generate_embeddings_batch

        return generate_embeddings_batch

    # Ingestion API
    if name == "DEFAULT_FILTERS":
        from raven.ingestion.api import DEFAULT_FILTERS

        return DEFAULT_FILTERS
    if name == "DEFAULT_SORT_ORDER":
        from raven.ingestion.api import DEFAULT_SORT_ORDER

        return DEFAULT_SORT_ORDER
    if name == "SEMANTIC_FILTERS":
        from raven.ingestion.api import SEMANTIC_FILTERS

        return SEMANTIC_FILTERS
    if name == "_create_session_with_retries":
        from raven.ingestion.api import _create_session_with_retries

        return _create_session_with_retries
    if name == "_get_openalex_base_url":
        from raven.ingestion.api import _get_openalex_base_url

        return _get_openalex_base_url
    if name == "fetch_work":
        from raven.ingestion.api import fetch_work

        return fetch_work

    # Identifier
    if name == "normalize_doi":
        from raven.ingestion.identifier import normalize_doi

        return normalize_doi
    if name == "normalize_identifier":
        from raven.ingestion.identifier import normalize_identifier

        return normalize_identifier

    # Metadata
    if name == "_prepare_paper_info":
        from raven.ingestion.metadata import _prepare_paper_info

        return _prepare_paper_info

    # Pipeline
    if name == "_get_existing_paper_info":
        from raven.ingestion.pipeline import _get_existing_paper_info

        return _get_existing_paper_info
    if name == "_handle_existing_paper":
        from raven.ingestion.pipeline import _handle_existing_paper

        return _handle_existing_paper
    if name == "ingest_paper":
        from raven.ingestion.pipeline import ingest_paper

        return ingest_paper
    if name == "ingest_search_results":
        from raven.ingestion.pipeline import ingest_search_results

        return ingest_search_results

    # Search
    if name == "search_works":
        from raven.ingestion.search import search_works

        return search_works
    if name == "search_works_semantic":
        from raven.ingestion.search import search_works_semantic

        return search_works_semantic
    if name == "search_works_keyword":
        from raven.ingestion.search_keyword import search_works_keyword

        return search_works_keyword

    # Text
    if name == "combine_title_abstract":
        from raven.ingestion.text import combine_title_abstract

        return combine_title_abstract
    if name == "format_search_result":
        from raven.ingestion.text import format_search_result

        return format_search_result
    if name == "undo_inverted_index":
        from raven.ingestion.text import undo_inverted_index

        return undo_inverted_index

    # Storage
    if name == "add_embedding":
        from raven.storage import add_embedding

        return add_embedding
    if name == "add_paper":
        from raven.storage import add_paper

        return add_paper
    if name == "get_embedding_exists":
        from raven.storage import get_embedding_exists

        return get_embedding_exists
    if name == "get_paper_id_by_identifier":
        from raven.storage import get_paper_id_by_identifier

        return get_paper_id_by_identifier
    if name == "update_paper":
        from raven.storage import update_paper

        return update_paper

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
    from raven.ingestion.metadata import _prepare_paper_info
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
