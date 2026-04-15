"""Identifier extraction utilities for Raven storage.

Extracts identifiers from OpenAlex work IDs using priority: doi > openalex > pmid > pmcid > mag.
"""


def extract_identifier(ids: dict[str, str] | None) -> str | None:
    """Extract identifier from OpenAlex work IDs using priority: doi > openalex > pmid > pmcid > mag.

    Args:
        ids: Dictionary of OpenAlex work IDs with keys like 'doi', 'openalex', 'pmid', 'pmcid', 'mag'.

    Returns:
        Formatted identifier string (e.g., 'doi:10.5281/zenodo.18201069') or None if no IDs available.
    """
    if ids is None:
        return None

    # Priority 1: DOI
    doi = ids.get("doi")
    if doi:
        # Strip https://doi.org/ and add doi: prefix
        doi_value = doi.replace("https://doi.org/", "").replace("http://doi.org/", "")
        return f"doi:{doi_value}"

    # Priority 2: OpenAlex
    openalex = ids.get("openalex")
    if openalex:
        # Strip https://openalex.org/ and add openalex: prefix
        openalex_value = openalex.replace("https://openalex.org/", "")
        return f"openalex:{openalex_value}"

    # Priority 3: PMID
    pmid = ids.get("pmid")
    if pmid:
        # Strip URL and add pmid: prefix
        pmid_value = pmid.replace("https://pubmed.ncbi.nlm.nih.gov/", "")
        return f"pmid:{pmid_value}"

    # Priority 4: PMCID
    pmcid = ids.get("pmcid")
    if pmcid:
        # Strip URL and add pmcid: prefix
        pmcid_value = pmcid.replace(
            "https://www.ncbi.nlm.nih.gov/pmc/articles/", ""
        ).replace("PMC", "")
        return f"pmcid:{pmcid_value}"

    # Priority 5: MAG
    mag = ids.get("mag")
    if mag:
        # Just add mag: prefix
        return f"mag:{mag}"

    # No IDs available
    return None
