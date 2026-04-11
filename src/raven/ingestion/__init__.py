"""Ingestion module - OpenAlex API + PDF processing for Raven."""

import requests
from pathlib import Path
from typing import Any

from raven.storage import add_paper


# Base URL for OpenAlex API
OPENALEX_API = "https://api.openalex.org/works"


def ingest_paper(db_path: Path, doi: str) -> dict[str, Any] | None:
    """Ingest a paper by DOI from OpenAlex."""
    # Clean DOI
    doi = doi.strip().lower()
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    elif doi.startswith("doi:"):
        doi = doi.replace("doi:", "")
    
    # Query OpenAlex API (requires doi: prefix)
    url = f"{OPENALEX_API}/doi:{doi}"
    response = requests.get(url, timeout=30)
    
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