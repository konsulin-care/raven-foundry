"""Identifier normalization utilities for OpenAlex API.

Handles DOI, OpenAlex ID, PMID, and MAG identifier formats.

Rules:
- Deduplicate using identifier before insertion
- Do not use LLMs in this module
"""

import logging

logger = logging.getLogger(__name__)

# DOI URL prefix constant
_DOI_URL_PREFIX = "https://doi.org/"


def normalize_doi(doi: str) -> str:
    """Normalize DOI by stripping URL prefixes and case normalizing."""
    doi = doi.strip().lower()
    if doi.startswith(_DOI_URL_PREFIX):
        doi = doi.replace(_DOI_URL_PREFIX, "")
    elif doi.startswith("doi:"):
        doi = doi.replace("doi:", "")
    return doi


def normalize_identifier(identifier: str) -> str:
    """Detect and normalize identifier type for OpenAlex API.

    Supported formats:
    - DOI: 10.5281/zenodo.18201069, doi:10.5281/zenodo.18201069, https://doi.org/10.5281/zenodo.18201069
    - OpenAlex: W7119934875, openalex:W7119934875, https://openalex.org/W7119934875
    - PMID: 29456894, pmid:29456894, https://pubmed.ncbi.nlm.nih.gov/29456894
    - MAG: 2741809807, mag:2741809807

    Default to OpenAlex ID format if unrecognized.

    Args:
        identifier: Raw identifier string from user.

    Returns:
        Normalized identifier with explicit prefix for OpenAlex API.
    """
    id = identifier.strip()

    # Already has explicit prefix
    for prefix in ("doi:", "openalex:", "pmid:", "mag:"):
        if id.lower().startswith(prefix):
            return id.lower()

    # DOI URL pattern (contains doi.org/)
    if "doi.org/" in id.lower():
        cleaned = id.lower().replace(_DOI_URL_PREFIX, "").replace("http://doi.org/", "")
        return f"doi:{cleaned}"

    # OpenAlex URL
    if "openalex.org/" in id.lower():
        cleaned = (
            id.lower()
            .replace("https://openalex.org/", "")
            .replace("http://openalex.org/", "")
        )
        return f"openalex:{cleaned}"

    # PubMed URL
    if "pubmed.ncbi.nlm.nih.gov/" in id.lower():
        cleaned = id.lower().replace("https://pubmed.ncbi.nlm.nih.gov/", "")
        return f"pmid:{cleaned}"

    # DOI pattern (contains /)
    if "/" in id:
        return f"doi:{id.lower()}"

    # PMID (digits only, 7+ digits)
    if id.isdigit() and len(id) >= 7:
        return f"pmid:{id}"

    # MAG (digits only)
    if id.isdigit():
        return f"mag:{id}"

    # OpenAlex ID (starts with W followed by digits)
    if id.upper().startswith("W") and len(id) > 1 and id[1:].isdigit():
        return f"openalex:{id.upper()}"

    # Default to OpenAlex ID (warn user to use explicit prefix)
    logger.warning(
        "Unrecognized identifier format '%s'. Treating as OpenAlex ID. "
        "Use explicit prefix (doi:, openalex:, pmid:, mag:) for clarity.",
        identifier,
    )
    return f"openalex:{id.upper()}"
