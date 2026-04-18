"""Text processing utilities for OpenAlex data.

Handles abstract reconstruction, result formatting, and text combination.

Rules:
- Do not use LLMs in this module
- Keep processing CPU-efficient
"""

from typing import Any


def combine_title_abstract(title: str, abstract: str | None) -> str:
    """Combine title and abstract for embedding generation.

    Args:
        title: Paper title.
        abstract: Paper abstract (may be None or empty).

    Returns:
        Combined text suitable for embedding generation.
    """
    if abstract and abstract.strip():
        return f"{title} {abstract}"
    return title


def undo_inverted_index(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruct original text from OpenAlex abstract_inverted_index.

    Optimized implementation - O(n) instead of O(n log n) by using
    direct indexing instead of sorting.

    Args:
        inverted_index: OpenAlex abstract_inverted_index dict

    Returns:
        Reconstructed text string
    """
    if not inverted_index:
        return ""

    # Find maximum index to pre-allocate result list
    max_index = 0
    for positions in inverted_index.values():
        if positions:
            max_index = max(max_index, max(positions))

    # Pre-allocate list with None placeholders (use str | None for type safety)
    result: list[str | None] = [None] * (max_index + 1)

    # Place each word at its position(s)
    for word, positions in inverted_index.items():
        for pos in positions:
            result[pos] = word

    # Filter out None and join with spaces
    return " ".join(word for word in result if word is not None)


def format_search_result(work: dict[str, Any]) -> dict[str, Any]:
    """Format OpenAlex work result for display/storage.

    Includes: Identifier, Year, Type, Citation, Open Access, Abstract, Embedding Text

    Args:
        work: Single work result from OpenAlex API

    Returns:
        Formatted dict with standardized keys
    """
    from raven.storage import extract_identifier

    # Reconstruct abstract from inverted index if available
    abstract = ""
    abstract_inverted = work.get("abstract_inverted_index")
    if abstract_inverted:
        abstract = undo_inverted_index(abstract_inverted)

    # Get title for embedding text generation
    title = work.get("title", "Untitled")

    # Extract identifier from work['ids'] using priority (doi > openalex > pmid > mag)
    identifier = extract_identifier(work.get("ids"))

    return {
        "identifier": identifier,
        "title": title,
        "type": work.get("type", "article"),
        "publication_year": work.get("publication_year"),
        "cited_by_count": work.get("cited_by_count", 0),
        "open_access": work.get("open_access", {}).get("is_oa", False),
        "abstract": abstract,
        "id": work.get("id"),
        "relevance_score": work.get("relevance_score"),
        "embedding_text": combine_title_abstract(title, abstract),
    }
