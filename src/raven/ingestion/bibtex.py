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

from pathlib import Path
from typing import Any

import bibtexparser

from raven.ingestion.bibtex_normalize import (
    get_field,
    normalize_doi,
    normalize_mag,
    normalize_openalex,
    normalize_pmcid,
    normalize_pmid,
)


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
    doi = get_field(entry, "doi", "DOI")
    if doi:
        doi_value = normalize_doi(doi)
        if doi_value:
            return f"doi:{doi_value}"

    # PMID - check common field names
    pmid = get_field(entry, "pmid", "PMID", "pubmed_id")
    if pmid:
        return f"pmid:{normalize_pmid(pmid)}"

    # PMCID - check common field names
    pmcid = get_field(entry, "pmcid", "PMCID", "pmc_id")
    if pmcid:
        return f"pmcid:{normalize_pmcid(pmcid)}"

    # MAG - check common field names
    mag = get_field(entry, "mag", "MAG", "microsoft_id")
    if mag:
        return f"mag:{normalize_mag(mag)}"

    # OpenAlex ID - check common field names
    openalex = get_field(entry, "openalex", "OPENALEX", "openalex_id")
    if openalex:
        return f"openalex:{normalize_openalex(openalex)}"

    return None


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
