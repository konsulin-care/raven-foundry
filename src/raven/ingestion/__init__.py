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

from pathlib import Path
from typing import Any

import requests

from raven.config import get_openalex_api_key, get_openalex_api_url
from raven.storage import add_paper


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
    url = f"{base_url}/works/doi:{doi}"
    headers = {"Authorization": f"Bearer {api_key}"}
    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code != 200:
        return None

    data = response.json()

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
