"""OpenAlex search operations for Raven.

Handles semantic, keyword, and hybrid search with rate limiting.

Rules:
- Do not use LLMs in this module
- Keep processing CPU-efficient
"""

import logging
from typing import Any

import requests

from raven.config import get_openalex_api_key
from raven.ingestion.api import (
    DEFAULT_SORT_ORDER,
    SEMANTIC_FILTERS,
    _create_session_with_retries,
    _get_openalex_base_url,
    _parse_search_query,
    _rate_limit_semantic,
)

logger = logging.getLogger(__name__)


def search_works(
    query: str,
    filter_str: str | None = None,
    page: int = 1,
    per_page: int = 50,
    sort: str = DEFAULT_SORT_ORDER,
    use_semantic: bool = True,
) -> dict[str, Any]:
    """Search works via OpenAlex API.

    Tries semantic search first, falls back to keyword search on rate limit.

    Args:
        query: Search query string
        filter_str: Additional OpenAlex filters (e.g., "publication_year:>2020")
        page: Page number (1-indexed)
        per_page: Results per page (max 100)
        sort: Sort order (default: relevance_score:desc)
        use_semantic: If True, try semantic first, then fallback to keyword

    Returns:
        Dict with 'results', 'meta' (pagination info), 'search_type' indicator
    """
    from raven.ingestion.api import DEFAULT_FILTERS

    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    session = _create_session_with_retries()

    # Try semantic search first if enabled
    if use_semantic:
        try:
            _rate_limit_semantic()

            # Build filters for semantic search (limited supported filters)
            semantic_filters = [SEMANTIC_FILTERS]
            if filter_str:
                semantic_filters.append(filter_str)
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
    if filter_str:
        filters.append(filter_str)
    combined_filter = ",".join(filters)

    search_type = "keyword"
    url = f"{base_url}/works"
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

        keyword_data: dict[str, Any] = response.json()
        keyword_data["search_type"] = search_type
        return keyword_data

    except requests.exceptions.RequestException as e:
        logger.error("Network error during search: %s", e)
        return {"results": [], "meta": {"count": 0}, "search_type": search_type}


def search_works_keyword(
    query: str,
    filter_str: str | None = None,
    page: int = 1,
    per_page: int = 50,
    sort: str = DEFAULT_SORT_ORDER,
) -> dict[str, Any]:
    """Keyword-only search (explicit).

    Args:
        query: Search query string
        filter_str: Additional OpenAlex filters
        page: Page number
        per_page: Results per page (max 100)
        sort: Sort order

    Returns:
        Dict with 'results', 'meta', 'search_type'='keyword'
    """
    from raven.ingestion.api import DEFAULT_FILTERS

    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    filters = [DEFAULT_FILTERS]
    if filter_str:
        filters.append(filter_str)
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
        "sort": DEFAULT_SORT_ORDER,
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
