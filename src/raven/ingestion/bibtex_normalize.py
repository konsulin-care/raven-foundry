"""BibTeX identifier normalization utilities.

Functions to normalize various identifier types from BibTeX entries.
"""

import re
from typing import Any


def get_field(entry: dict[str, Any], field_name: str, *alternates: str) -> str | None:
    """Get a field value from a dictionary, trying multiple field name variants.

    Args:
        entry: Dictionary to search.
        field_name: Primary field name to try.
        *alternates: Alternate field names to try if primary not found.

    Returns:
        First non-empty value found, or None.
    """
    for name in (field_name, *alternates):
        value: str | None = entry.get(name)  # type: ignore[assignment]
        if value:
            return value
    return None


def normalize_doi(value: str) -> str | None:
    """Normalize DOI value.

    Args:
        value: Raw DOI value from BibTeX.

    Returns:
        Normalized DOI without URL prefix, or None if invalid.
    """
    if not value:
        return None
    # Strip common prefixes
    value = value.strip()
    value = re.sub(r"^doi:", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^https?://doi\.org/", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^http://doi\.org/", "", value, flags=re.IGNORECASE)
    # Validate basic DOI format
    if re.match(r"^10\.\d{4,}/", value):
        return value
    return None


def normalize_pmid(value: str) -> str:
    """Normalize PMID value.

    Args:
        value: Raw PMID value from BibTeX.

    Returns:
        Normalized PMID (digits only).
    """
    if not value:
        return ""
    # Strip non-digit characters
    return re.sub(r"\D", "", value.strip())


def normalize_pmcid(value: str) -> str:
    """Normalize PMCID value.

    Args:
        value: Raw PMCID value from BibTeX.

    Returns:
        Normalized PMCID (with PMC prefix).
    """
    if not value:
        return ""
    value = value.strip()
    # Ensure PMC prefix
    if not value.upper().startswith("PMC"):
        value = f"PMC{value}"
    # Strip non-alphanumeric (keep PMC and digits)
    return re.sub(r"[^A-Za-z0-9]", "", value)


def normalize_mag(value: str) -> str:
    """Normalize MAG (Microsoft Academic Graph) ID value.

    Args:
        value: Raw MAG ID from BibTeX.

    Returns:
        Normalized MAG ID (digits only).
    """
    if not value:
        return ""
    # MAG IDs are numeric
    return re.sub(r"\D", "", value.strip())


def normalize_openalex(value: str) -> str:
    """Normalize OpenAlex ID value.

    Args:
        value: Raw OpenAlex ID from BibTeX.

    Returns:
        Normalized OpenAlex ID (W prefix + digits).
    """
    if not value:
        return ""
    value = value.strip()
    # Strip URL prefix
    value = re.sub(r"^https?://openalex\.org/", "", value, flags=re.IGNORECASE)
    # Ensure W prefix
    if not value.upper().startswith("W"):
        value = f"W{value}"
    # Keep only alphanumeric
    return re.sub(r"[^A-Za-z0-9]", "", value)
