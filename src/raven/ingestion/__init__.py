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
from pathlib import Path
from typing import Any

import requests

from raven.config import get_openalex_api_key, get_openalex_api_url
from raven.storage import add_paper

# Configure logging
logger = logging.getLogger(__name__)


def _get_openalex_base_url() -> str:
    """Get OpenAlex API base URL from config."""
    return get_openalex_api_url()


def ingest_paper(db_path: Path, doi: str) -> dict[str, Any] | None:
    """Ingest a paper by DOI from OpenAlex."""
    # Get API configuration
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    # Clean DOI
    doi = doi.strip().lower()
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    elif doi.startswith("doi:"):
        doi = doi.replace("doi:", "")

    # Query OpenAlex API (requires doi: prefix)
    url = f"{base_url}/works/doi:{doi}?api_key={api_key}"
    try:
        response = requests.get(url, timeout=30)
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
