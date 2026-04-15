"""Metadata extraction from OpenAlex work results.

Handles extraction of paper metadata fields from OpenAlex API responses.

Rules:
- Do not use LLMs in this module
"""

from typing import Any

from raven.ingestion.text import combine_title_abstract, undo_inverted_index


def _extract_paper_metadata(work: dict[str, Any]) -> dict[str, Any]:
    """Extract metadata fields from OpenAlex work.

    Args:
        work: Single work result from OpenAlex API.

    Returns:
        Dict with extracted metadata fields.
    """
    from raven.storage import extract_identifier

    # Extract identifier using priority: doi > openalex > pmid > mag
    identifier = extract_identifier(work.get("ids"))

    # Extract title
    title = work.get("title", "Untitled")

    # Reconstruct abstract from inverted index if available
    abstract = ""
    abstract_inverted = work.get("abstract_inverted_index")
    if abstract_inverted:
        abstract = undo_inverted_index(abstract_inverted)

    # Reconstruct authors from authorship data
    authors_list = work.get("authorships", [])
    authors = (
        ", ".join(a.get("author", {}).get("display_name", "") for a in authors_list)
        or None
    )

    return {
        "identifier": identifier,
        "title": title,
        "paper_type": work.get("type", "article"),
        "abstract": abstract,
        "authors": authors,
        "publication_year": work.get("publication_year"),
        "venue": work.get("host_venue", {}).get("display_name"),
        "openalex_id": work.get("id"),
    }


def _prepare_paper_info(work: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Prepare paper info dict and embedding text from OpenAlex work result.

    Args:
        work: Single work result from OpenAlex search API.

    Returns:
        Tuple of (paper_info dict, embedding_text string).
    """
    # Extract metadata
    metadata = _extract_paper_metadata(work)

    # Get title and abstract for embedding text
    title = metadata.get("title", "Untitled")
    abstract = metadata.get("abstract", "")

    # Build paper_info dict for storage
    paper_info = {
        "identifier": metadata.get("identifier"),
        "title": title,
        "authors": metadata.get("authors"),
        "abstract": abstract,
        "publication_year": metadata.get("publication_year"),
        "venue": metadata.get("venue"),
        "openalex_id": metadata.get("openalex_id"),
        "paper_type": metadata.get("paper_type", "article"),
    }

    # Generate embedding text
    embedding_text = combine_title_abstract(title, abstract)

    return paper_info, embedding_text
