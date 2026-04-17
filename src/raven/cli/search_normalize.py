"""Search result normalization utilities for Raven CLI."""

from typing import Any


def normalize_local_result(
    paper: dict[str, Any], use_vector: bool = False
) -> dict[str, Any]:
    """Normalize local search result.

    Args:
        paper: Paper dictionary from local search.
        use_vector: If True, calculate similarity from distance.
                  If False, use fixed keyword search scores.

    Returns:
        Normalized paper dictionary.
    """
    if use_vector:
        distance = paper.get("distance", 1.0)
        similarity = 1.0 - distance
        relevance_score = similarity * 1000
        original_score = similarity
    else:
        relevance_score = 500
        original_score = 0.5

    return {
        "title": paper.get("title", "Untitled"),
        "identifier": paper.get("identifier"),
        "year": paper.get("year"),
        "type": paper.get("type", "article"),
        "abstract": paper.get("abstract"),
        "source": "local",
        "relevance_score": relevance_score,
        "original_score": original_score,
    }


def normalize_local_vector(paper: dict[str, Any]) -> dict[str, Any]:
    """Normalize local vector search result."""
    return normalize_local_result(paper, use_vector=True)


def normalize_local_keyword(paper: dict[str, Any]) -> dict[str, Any]:
    """Normalize local keyword search result."""
    return normalize_local_result(paper, use_vector=False)


def normalize_openalex(
    work: dict[str, Any], formatted: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Normalize OpenAlex search result.

    Args:
        work: Original OpenAlex work dictionary.
        formatted: Pre-formatted result from format_search_result.
                   If None, extracts data from work directly.

    Returns:
        Normalized paper dictionary.
    """
    # Use provided formatted data or extract from work for backward compatibility
    if formatted is None:
        formatted = {
            "title": work.get("title", "Untitled"),
            "identifier": work.get("identifier"),
            "year": work.get("publication_year"),
            "type": work.get("type", "article"),
            "abstract": work.get("abstract"),
            "relevance_score": work.get("relevance_score", 0.0),
            "cited_by_count": work.get("cited_by_count"),
            "open_access": work.get("open_access"),
        }

    original_score = formatted.get("relevance_score", 0.0)
    relevance_score = (original_score or 0.0) * 1000

    # Safely extract venue
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = source.get("display_name") if isinstance(source, dict) else None

    return {
        "title": formatted.get("title", "Untitled"),
        "identifier": formatted.get("identifier"),
        "year": formatted.get("year") or formatted.get("publication_year"),
        "type": formatted.get("type", "article"),
        "abstract": formatted.get("abstract"),
        "authors": work.get("authorships"),
        "venue": venue,
        "source": "openalex",
        "relevance_score": relevance_score,
        "original_score": original_score,
        "cited_by_count": formatted.get("cited_by_count"),
        "open_access": formatted.get("open_access"),
    }
