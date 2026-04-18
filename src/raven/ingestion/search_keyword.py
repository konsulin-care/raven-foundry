"""OpenAlex keyword-only search operations."""

import logging
from typing import Any

import requests

from raven.config import get_openalex_api_key
from raven.ingestion.api import DEFAULT_FILTERS, DEFAULT_SORT_ORDER, _parse_search_query
from raven.ingestion.search_utils import (
    create_session_with_retries,
    get_openalex_base_url,
)

logger = logging.getLogger(__name__)


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
    api_key = get_openalex_api_key()
    base_url = get_openalex_base_url()

    filters = [DEFAULT_FILTERS]
    if filter_str:
        filters.append(filter_str)
    combined_filter = ",".join(filters)

    session = create_session_with_retries()
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
