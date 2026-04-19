"""Search utilities for Raven ingestion.

Shared components for OpenAlex search operations.

Rules:
- Do not use LLMs in this module
- Keep processing CPU-efficient
"""

import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from raven.config import get_openalex_api_url

_semantic_last_request_time: float = 0.0


def create_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic and backoff."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    return session


def get_openalex_base_url() -> str:
    """Get OpenAlex API base URL from config."""
    return get_openalex_api_url()


def rate_limit_semantic() -> None:
    """Apply rate limiting for semantic search."""
    global _semantic_last_request_time
    elapsed = time.time() - _semantic_last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _semantic_last_request_time = time.time()
