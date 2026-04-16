"""Search client utilities for Raven ingestion.

Shared components for OpenAlex search operations.
"""

import logging
from typing import Any

from raven.config import get_openalex_api_key
from raven.ingestion.api import (
    _create_session_with_retries,
    _get_openalex_base_url,
    _rate_limit_semantic,
)

logger = logging.getLogger(__name__)


def get_search_client() -> tuple[str, Any, Any]:
    """Get common search client components.

    Returns:
        Tuple of (api_key, base_url, session).
    """
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()
    session = _create_session_with_retries()
    return api_key, base_url, session


def parse_search_response(response: Any, search_type: str) -> dict[str, Any]:
    """Parse OpenAlex search response.

    Args:
        response: Requests response object.
        search_type: Type of search ('semantic' or 'keyword').

    Returns:
        Parsed response dict with search_type.
    """
    if response.status_code != 200:
        logger.error(
            "OpenAlex %s search error: status %s", search_type, response.status_code
        )
        return {"results": [], "meta": {"count": 0}, "search_type": search_type}

    data: dict[str, Any] = response.json()
    data["search_type"] = search_type
    return data


def check_rate_limit_semantic() -> None:
    """Check and enforce rate limit for semantic search."""
    _rate_limit_semantic()
