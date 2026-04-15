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
- __init__.py: Re-exports for backward compatibility
"""

import logging

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

# Re-export config functions used in tests
from raven.config import get_openalex_api_key, get_openalex_api_url

# Re-export embeddings functions for backward compatibility
from raven.embeddings import (
    generate_embedding,
    generate_embeddings_batch,
)

# Re-export from submodules for backward compatibility
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
from raven.ingestion.search_keyword import (
    search_works_keyword,
)
from raven.ingestion.text import (
    combine_title_abstract,
    format_search_result,
    undo_inverted_index,
)

# Re-export storage functions for backward compatibility
from raven.storage import (
    add_embedding,
    add_paper,
    get_embedding_exists,
    get_paper_id_by_identifier,
    update_paper,
)

# Re-export logger for backward compatibility
logger = logging.getLogger(__name__)
