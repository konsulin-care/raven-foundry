"""BibTeX parsing module for Raven ingestion.

Responsibilities:
- Parse BibTeX files into standardized JSON
- Extract supported identifiers from entries
- Filter entries with valid identifiers for ingestion

Supported identifiers:
- DOI: 10.5281/zenodo.18201069, doi:10.5281/zenodo.18201069
- PMID: 29456894, pmid:29456894
- PMCID: PMC1234567, pmcid:PMC1234567
- MAG: 2741809807, mag:2741809807
- OpenAlex ID: W7119934875, openalex:W7119934875
"""

import re
from pathlib import Path
from typing import Any

import bibtexparser


def _get_field(entry: dict[str, Any], field_name: str, *alternates: str) -> str | None:
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


def parse_bibtex_file(file_path: Path) -> list[dict[str, Any]]:
    """Parse a BibTeX file and return entries as list of dictionaries.

    Args:
        file_path: Path to the BibTeX file.

    Returns:
        List of dictionaries representing each BibTeX entry.
        Each dict contains all fields from the entry plus '_key' (citation key).
    """
    with open(file_path, "r", encoding="utf-8") as f:
        library = bibtexparser.load(f)
    entries = []
    for entry in library.entries:
        # Entry is already a dict, preserve all fields and add citation key
        entry_dict = dict(entry)
        entry_dict["_key"] = entry.get("ID", "")
        entries.append(entry_dict)
    return entries


def extract_identifier_from_bibtex(entry: dict[str, Any]) -> str | None:
    """Extract a supported identifier from a BibTeX entry.

    Checks fields in priority order: doi > pmid > pmcid > mag > openalex.

    Args:
        entry: BibTeX entry as a dictionary.

    Returns:
        Normalized identifier string (e.g., 'doi:10.5281/...') or None.
    """
    # DOI - check common field names
    doi = _get_field(entry, "doi", "DOI")
    if doi:
        doi_value = _normalize_doi(doi)
        if doi_value:
            return f"doi:{doi_value}"

    # PMID - check common field names
    pmid = _get_field(entry, "pmid", "PMID", "pubmed_id")
    if pmid:
        return f"pmid:{_normalize_pmid(pmid)}"

    # PMCID - check common field names
    pmcid = _get_field(entry, "pmcid", "PMCID", "pmc_id")
    if pmcid:
        return f"pmcid:{_normalize_pmcid(pmcid)}"

    # MAG - check common field names
    mag = _get_field(entry, "mag", "MAG", "microsoft_id")
    if mag:
        return f"mag:{_normalize_mag(mag)}"

    # OpenAlex ID - check common field names
    openalex = _get_field(entry, "openalex", "OPENALEX", "openalex_id")
    if openalex:
        return f"openalex:{_normalize_openalex(openalex)}"

    return None


def _normalize_doi(value: str) -> str | None:
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


def _normalize_pmid(value: str) -> str:
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


def _normalize_pmcid(value: str) -> str:
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


def _normalize_mag(value: str) -> str:
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


def _normalize_openalex(value: str) -> str:
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


def filter_valid_entries(
    entries: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Filter BibTeX entries to find those with valid identifiers.

    Args:
        entries: List of BibTeX entries as dictionaries.

    Returns:
        Tuple of (valid_entries, invalid_entries).
        Valid entries have a normalized identifier added to their dict.
    """
    valid = []
    invalid = []

    for entry in entries:
        identifier = extract_identifier_from_bibtex(entry)
        if identifier:
            entry["_identifier"] = identifier
            valid.append(entry)
        else:
            invalid.append(entry)

    return valid, invalid
