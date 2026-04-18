"""OpenAlex API client base for Raven.

Handles API communication, session creation, and rate limiting.

Rules:
- Do not use LLMs in this module
- Keep processing CPU-efficient
"""

import logging
import time
from typing import Any, cast
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from raven.config import get_openalex_api_key, get_openalex_api_url

logger = logging.getLogger(__name__)

# Default filters for search results
DEFAULT_FILTERS = "is_oa:true"
SEMANTIC_FILTERS = "is_oa:true"

# Default sort order for search results
DEFAULT_SORT_ORDER = "relevance_score:desc"

# Rate limiting for semantic search (1 request per second)
_semantic_last_request_time: float = 0.0


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
