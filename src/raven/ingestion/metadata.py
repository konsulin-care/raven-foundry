"""Metadata extraction from OpenAlex work results.

Handles extraction of paper metadata fields from OpenAlex API responses.

Rules:
- Do not use LLMs in this module
"""

from typing import Any

from raven.ingestion.text import combine_title_abstract, undo_inverted_index


def _extract_author_data(authorship: dict[str, Any], order: int) -> dict[str, Any]:
    """Extract author data from OpenAlex authorship.

    Args:
        authorship: Single authorship dict from OpenAlex work.
        order: Author order in the paper.

    Returns:
        Dict with author fields: id, name, orcid, is_corresponding, order.
    """
    author = authorship.get("author", {})

    # Extract author ID (remove URL prefix)
    author_id = author.get("id", "")
    if author_id:
        author_id = author_id.replace("https://openalex.org/", "")

    # Extract ORCID (remove URL prefix)
    orcid = author.get("orcid", "")
    if orcid:
        orcid = orcid.replace("https://orcid.org/", "")

    name = author.get("display_name", "")
    is_corresponding = 1 if authorship.get("is_corresponding") else 0

    return {
        "id": author_id,
        "name": name,
        "orcid": orcid if orcid else None,
        "is_corresponding": is_corresponding,
        "order": order,
    }


def extract_paper_metadata(work: dict[str, Any]) -> dict[str, Any]:
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

    # Extract authordata from authorship
    authors_data = []
    for idx, auth in enumerate(work.get("authorships", [])):
        author_info = _extract_author_data(auth, idx)
        if author_info["name"]:  # Only add if name exists
            authors_data.append(author_info)

    # For backward compatibility, also create comma-separated string
    authors = ", ".join(a["name"] for a in authors_data) or None

    return {
        "identifier": identifier,
        "title": title,
        "paper_type": work.get("type", "article"),
        "abstract": abstract,
        "authors": authors,
        "authors_data": authors_data,
        "year": work.get("publication_year"),
        "source": work.get("primary_location", {})
        .get("source", {})
        .get("display_name"),
    }


def prepare_paper_info(work: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Prepare paper info dict and embedding text from OpenAlex work result.

    Args:
        work: Single work result from OpenAlex search API.

    Returns:
        Tuple of (paper_info dict, embedding_text string).
    """
    # Extract metadata
    metadata = extract_paper_metadata(work)

    # Get title and abstract for embedding text
    title = metadata.get("title", "Untitled")
    abstract = metadata.get("abstract", "")

    # Build paper_info dict for storage
    paper_info = {
        "identifier": metadata.get("identifier"),
        "title": title,
        "authors": metadata.get("authors"),
        "authors_data": metadata.get("authors_data"),
        "abstract": abstract,
        "year": metadata.get("year"),
        "source": metadata.get("source"),
        "paper_type": metadata.get("paper_type", "article"),
    }

    # Generate embedding text
    embedding_text = combine_title_abstract(title, abstract)

    return paper_info, embedding_text
