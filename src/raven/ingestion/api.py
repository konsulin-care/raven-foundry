"""OpenAlex API client base for Raven.

Handles API communication, session creation, and rate limiting.

Rules:
- Do not use LLMs in this module
- Keep processing CPU-efficient
"""

import logging
from typing import Any, cast
from urllib.parse import quote

import requests

from raven.config import get_openalex_api_key
from raven.ingestion.search_utils import (
    create_session_with_retries,
    get_openalex_base_url,
    rate_limit_semantic,
)

logger = logging.getLogger(__name__)

DEFAULT_FILTERS = "is_oa:true"
SEMANTIC_FILTERS = "is_oa:true"

DEFAULT_SORT_ORDER = "relevance_score:desc"

_create_session_with_retries = create_session_with_retries
_get_openalex_base_url = get_openalex_base_url
_rate_limit_semantic = rate_limit_semantic


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


def fetch_work(identifier: str) -> dict[str, Any] | None:
    """Fetch a single work by identifier from OpenAlex API.

    Args:
        identifier: Normalized identifier (doi:..., openalex:..., etc.)

    Returns:
        Work dict from OpenAlex, or None on failure.
    """
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    encoded_id = quote(identifier, safe="")
    url = f"{base_url}/works/{encoded_id}"

    session = _create_session_with_retries()
    try:
        response = session.get(url, params={"api_key": api_key}, timeout=30)
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching paper: %s", e)
        return None

    if response.status_code != 200:
        logger.error("OpenAlex API error: status %s", response.status_code)
        return None

    try:
        return cast(dict[str, Any], response.json())
    except requests.exceptions.JSONDecodeError as e:
        logger.error("Failed to parse response: %s", e)
        return None
