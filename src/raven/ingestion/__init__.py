"""Ingestion module - OpenAlex API + PDF processing for Raven.

Environment (from .env):
- OPENALEX_API_KEY: Required. Get from https://openalex.org/
- OPENALEX_API_URL: Optional. Defaults to https://api.openalex.org

Responsibilities:
- Query OpenAlex API
- Download PDFs
- Convert PDF → Markdown (MarkItDown)
- Clean extracted text

Rules:
- Deduplicate using DOI before insertion
- Do not use LLMs in this module
- Keep processing CPU-efficient
- Ensure ingestion integrates cleanly with CLI workflow
"""

import logging
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from raven.config import get_openalex_api_key, get_openalex_api_url
from raven.storage import add_paper

# Default filters for search results
# Note: Semantic search has limited filter support (no has_doi), so we use separate filters
DEFAULT_FILTERS = "is_oa:true,has_doi:true"  # For keyword search
SEMANTIC_FILTERS = "is_oa:true"  # For semantic search (limited to: is_oa, has_abstract, has_fulltext, etc.)

# Configure logging
logger = logging.getLogger(__name__)


def _create_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic and backoff."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    # Only use HTTPS - never fallback to insecure HTTP
    session.mount("https://", adapter)
    return session


def _get_openalex_base_url() -> str:
    """Get OpenAlex API base URL from config."""
    return get_openalex_api_url()


def normalize_doi(doi: str) -> str:
    """Normalize DOI by stripping URL prefixes and case normalizing."""
    doi = doi.strip().lower()
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    elif doi.startswith("doi:"):
        doi = doi.replace("doi:", "")
    return doi


def ingest_paper(db_path: Path, doi: str) -> dict[str, Any] | None:
    """Ingest a paper by DOI from OpenAlex."""
    # Get API configuration
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    # Clean DOI
    doi = normalize_doi(doi)

    # Query OpenAlex API (requires doi: prefix)
    url = f"{base_url}/works/doi:{doi}?api_key={api_key}"

    # Use session with retry logic
    session = _create_session_with_retries()
    try:
        response = session.get(url, timeout=30)
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching paper: %s", e)
        return None

    if response.status_code != 200:
        logger.error("OpenAlex API error: status %s", response.status_code)
        return None

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        logger.error("Failed to parse response: %s", e)
        return None

    # Extract metadata
    title = data.get("title", "Untitled")
    paper_type = data.get("type", "article")

    # Add to database
    add_paper(db_path, doi, title, paper_type)

    return {
        "doi": doi,
        "title": title,
        "type": paper_type,
    }


# Rate limiting for semantic search (1 request per second)
_semantic_last_request_time: float = 0.0


def _rate_limit_semantic() -> None:
    """Apply rate limiting for semantic search."""
    global _semantic_last_request_time
    elapsed = time.time() - _semantic_last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _semantic_last_request_time = time.time()


def _parse_search_query(query: str) -> str:
    """Parse user query to OpenAlex search syntax.

    Handles:
    - Boolean operators (AND, OR, NOT) - passed through
    - Quoted phrases - kept as exact match
    - Wildcards (*, ?) - passed through
    - Fuzzy search (~N) - passed through
    """
    # Normalize whitespace
    query = " ".join(query.split())
    return query


def search_works(
    query: str,
    filter: str | None = None,
    page: int = 1,
    per_page: int = 50,
    sort: str = "relevance_score:desc",
    use_semantic: bool = True,
) -> dict[str, Any]:
    """Search works via OpenAlex API.

    Tries semantic search first, falls back to keyword search on rate limit.

    Args:
        query: Search query string
        filter: Additional OpenAlex filters (e.g., "publication_year:>2020")
        page: Page number (1-indexed)
        per_page: Results per page (max 100)
        sort: Sort order (default: relevance_score:desc)
        use_semantic: If True, try semantic first, then fallback to keyword

    Returns:
        Dict with 'results', 'meta' (pagination info), 'search_type' indicator
    """
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    session = _create_session_with_retries()

    # Try semantic search first if enabled
    if use_semantic:
        try:
            _rate_limit_semantic()

            # Build filters for semantic search (limited supported filters)
            semantic_filters = [SEMANTIC_FILTERS]
            if filter:
                semantic_filters.append(filter)
            combined_semantic_filter = ",".join(semantic_filters)

            url = f"{base_url}/works"
            params: dict[str, Any] = {
                "search.semantic": query,
                "filter": combined_semantic_filter,
                "sort": sort,
                "per_page": min(per_page, 50),  # Semantic max 50
                "page": page,
                "api_key": api_key,
            }

            response = session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                data["search_type"] = "semantic"
                return data
            elif response.status_code == 429:
                logger.info("Semantic search rate limited, falling back to keyword")
            else:
                logger.warning(
                    "Semantic search failed: status %s, falling back to keyword",
                    response.status_code,
                )
        except requests.exceptions.RequestException as e:
            logger.warning("Semantic search error: %s, falling back to keyword", e)

    # Fallback to keyword search (use full filters)
    filters = [DEFAULT_FILTERS]
    if filter:
        filters.append(filter)
    combined_filter = ",".join(filters)

    search_type = "keyword"
    url = f"{base_url}/works"
    # Note: params shadows the semantic branch's params but they're in different branches
    keyword_params: dict[str, Any] = {
        "search": _parse_search_query(query),
        "filter": combined_filter,
        "sort": sort,
        "per_page": min(per_page, 100),  # Keyword max 100
        "page": page,
        "api_key": api_key,
    }

    try:
        response = session.get(url, params=keyword_params, timeout=30)

        if response.status_code != 200:
            logger.error("OpenAlex search error: status %s", response.status_code)
            return {"results": [], "meta": {"count": 0}, "search_type": search_type}

        # Note: data shadows the semantic branch's data but they're in different branches
        keyword_data: dict[str, Any] = response.json()
        keyword_data["search_type"] = search_type
        return keyword_data

    except requests.exceptions.RequestException as e:
        logger.error("Network error during search: %s", e)
        return {"results": [], "meta": {"count": 0}, "search_type": search_type}


def search_works_keyword(
    query: str,
    filter: str | None = None,
    page: int = 1,
    per_page: int = 50,
    sort: str = "relevance_score:desc",
) -> dict[str, Any]:
    """Keyword-only search (explicit).

    Args:
        query: Search query string
        filter: Additional OpenAlex filters
        page: Page number
        per_page: Results per page (max 100)
        sort: Sort order

    Returns:
        Dict with 'results', 'meta', 'search_type'='keyword'
    """
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    filters = [DEFAULT_FILTERS]
    if filter:
        filters.append(filter)
    combined_filter = ",".join(filters)

    session = _create_session_with_retries()
    url = f"{base_url}/works"
    params: dict[str, Any] = {
        "search": _parse_search_query(query),
        "filter": combined_filter,
        "sort": sort,
        "per_page": min(per_page, 100),
        "page": page,
        "api_key": api_key,
    }

    try:
        response = session.get(url, params=params, timeout=30)

        if response.status_code != 200:
            logger.error(
                "OpenAlex keyword search error: status %s", response.status_code
            )
            return {"results": [], "meta": {"count": 0}, "search_type": "keyword"}

        data: dict[str, Any] = response.json()
        data["search_type"] = "keyword"
        return data

    except requests.exceptions.RequestException as e:
        logger.error("Network error during keyword search: %s", e)
        return {"results": [], "meta": {"count": 0}, "search_type": "keyword"}


def search_works_semantic(
    query: str,
    per_page: int = 50,
) -> dict[str, Any]:
    """Semantic-only search (explicit).

    Note: Limited to 1 request per second, max 50 results.

    Args:
        query: Semantic search query
        per_page: Results per page (max 50)

    Returns:
        Dict with 'results', 'meta', 'search_type'='semantic'
    """
    _rate_limit_semantic()

    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    session = _create_session_with_retries()
    url = f"{base_url}/works"
    params: dict[str, Any] = {
        "search.semantic": query,
        "filter": SEMANTIC_FILTERS,
        "sort": "relevance_score:desc",
        "per_page": min(per_page, 50),
        "api_key": api_key,
    }

    try:
        response = session.get(url, params=params, timeout=30)

        if response.status_code != 200:
            logger.error(
                "OpenAlex semantic search error: status %s", response.status_code
            )
            return {"results": [], "meta": {"count": 0}, "search_type": "semantic"}

        data: dict[str, Any] = response.json()
        data["search_type"] = "semantic"
        return data

    except requests.exceptions.RequestException as e:
        logger.error("Network error during semantic search: %s", e)
        return {"results": [], "meta": {"count": 0}, "search_type": "semantic"}


def undo_inverted_index(inverted_index: dict[str, list[int]]) -> str:
    """Reconstruct original text from OpenAlex abstract_inverted_index.

    Optimized implementation - O(n) instead of O(n log n) by using
    direct indexing instead of sorting.

    Args:
        inverted_index: OpenAlex abstract_inverted_index dict

    Returns:
        Reconstructed text string
    """
    if not inverted_index:
        return ""

    # Find maximum index to pre-allocate result list
    max_index = 0
    for positions in inverted_index.values():
        if positions:
            max_index = max(max_index, max(positions))

    # Pre-allocate list with None placeholders (use str | None for type safety)
    result: list[str | None] = [None] * (max_index + 1)

    # Place each word at its position(s)
    for word, positions in inverted_index.items():
        for pos in positions:
            result[pos] = word

    # Filter out None and join with spaces
    return " ".join(word for word in result if word is not None)


def format_search_result(work: dict[str, Any]) -> dict[str, Any]:
    """Format OpenAlex work result for display/storage.

    Includes: DOI, Year, Type, Citation, Open Access, Abstract
    """
    # Reconstruct abstract from inverted index if available
    abstract = ""
    abstract_inverted = work.get("abstract_inverted_index")
    if abstract_inverted:
        abstract = undo_inverted_index(abstract_inverted)

    return {
        "doi": work.get("doi"),
        "title": work.get("title", "Untitled"),
        "type": work.get("type", "article"),
        "publication_year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count", 0),
        "open_access": work.get("open_access", {}).get("is_oa", False),
        "abstract": abstract,
        "id": work.get("id"),
        "relevance_score": work.get("relevance_score"),
    }
