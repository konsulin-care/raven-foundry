"""Search orchestrator for Raven CLI - OpenAlex default with local option."""

import logging
from pathlib import Path
from typing import Any

from raven.cli.search_db import check_batch_ingested
from raven.cli.search_display import display_json, display_text
from raven.embeddings import generate_embedding
from raven.ingestion import format_search_result, search_works
from raven.storage.embedding import search_by_embedding

logger = logging.getLogger(__name__)

LOCAL_MAX_RESULTS = 10
LOCAL_MAX_DISTANCE = 0.1


def search_with_fallback(
    db_path: Path,
    query: str,
    local: bool,
    keyword: bool,
    use_semantic: bool,
    filter_str: str | None,
    page: int,
    per_page: int,
    sort: str,
    text_output: bool,
) -> None:
    """Search with local-only or OpenAlex default behavior."""
    if local:
        _search_local_only(db_path, query, keyword, text_output)
    else:
        _search_openalex(
            db_path, query, filter_str, page, per_page, sort, use_semantic, text_output
        )


def _search_local_only(
    db_path: Path, query: str, keyword: bool, text_output: bool
) -> None:
    """Search local database only."""
    if keyword:
        from raven.storage.paper import search_papers

        results = search_papers(db_path, query)
        normalized = [_normalize_local_keyword(r) for r in results]
        closest_info = None
    else:
        normalized, closest_info = _fetch_local_results(db_path, query, keyword=False)

    total = len(normalized)
    if text_output:
        display_text(
            normalized, total, page=1, per_page=total, closest_info=closest_info
        )
    else:
        display_json(normalized, closest_info=closest_info)


def _search_openalex(
    db_path: Path,
    query: str,
    filter_str: str | None,
    page: int,
    per_page: int,
    sort: str,
    use_semantic: bool,
    text_output: bool,
) -> None:
    """Search OpenAlex and check ingestion status."""
    openalex_results = _fetch_openalex_results(
        query, filter_str, page, per_page, use_semantic
    )

    # Batch check ingestion status (single SQL query)
    ingested_ids = check_batch_ingested(db_path, openalex_results)

    # Mark ingested status
    for r in openalex_results:
        identifier = r.get("identifier")
        r["ingested"] = identifier is not None and identifier.lower() in ingested_ids

    # Apply pagination
    total = len(openalex_results)
    start = (page - 1) * per_page
    end = start + per_page
    paginated = openalex_results[start:end]

    if text_output:
        display_text(paginated, total, page, per_page)
    else:
        display_json(paginated)


def _fetch_local_results(
    db_path: Path, query: str, keyword: bool
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Fetch local results with distance filter."""
    if keyword:
        from raven.storage.paper import search_papers

        results = search_papers(db_path, query)
        return ([_normalize_local_keyword(r) for r in results], None)

    embedding = generate_embedding(query)
    results = search_by_embedding(db_path, embedding, top_k=LOCAL_MAX_RESULTS)

    if not results:
        return ([], None)

    filtered = []
    closest = None
    for r in results:
        distance = r.get("distance", 1.0)
        if closest is None:
            closest = r
        if distance < LOCAL_MAX_DISTANCE:
            filtered.append(r)

    closest_info = None
    if not filtered and closest:
        distance = closest.get("distance", 1.0)
        closest_info = {
            "title": closest.get("title", "Untitled"),
            "distance": distance,
            "relevance": 1.0 - distance,
            "identifier": closest.get("identifier"),
        }

    return ([_normalize_local_vector(r) for r in filtered], closest_info)


def _fetch_openalex_results(
    query: str, filter_str: str | None, page: int, per_page: int, use_semantic: bool
) -> list[dict[str, Any]]:
    """Fetch OpenAlex results."""
    oversfetch_per_page = max(per_page * 2, 100)
    result_data = search_works(
        query=query,
        filter_str=filter_str,
        page=page,
        per_page=oversfetch_per_page,
        sort="relevance_score:desc",
        use_semantic=use_semantic,
    )
    results = result_data.get("results", [])
    return [_normalize_openalex(r) for r in results]


def _normalize_local_result(
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
        "publication_year": paper.get("publication_year"),
        "type": paper.get("type", "article"),
        "abstract": paper.get("abstract"),
        "source": "local",
        "relevance_score": relevance_score,
        "original_score": original_score,
    }


# Backward compatibility aliases
def _normalize_local_vector(paper: dict[str, Any]) -> dict[str, Any]:
    """Normalize local vector search result."""
    return _normalize_local_result(paper, use_vector=True)


def _normalize_local_keyword(paper: dict[str, Any]) -> dict[str, Any]:
    """Normalize local keyword search result."""
    return _normalize_local_result(paper, use_vector=False)


def _normalize_openalex(work: dict[str, Any]) -> dict[str, Any]:
    """Normalize OpenAlex search result."""
    formatted = format_search_result(work)
    original_score = formatted.get("relevance_score", 0.0)
    relevance_score = (original_score or 0.0) * 1000

    # Safely extract venue
    primary_location = work.get("primary_location") or {}
    source = primary_location.get("source") or {}
    venue = source.get("display_name") if isinstance(source, dict) else None

    return {
        "title": formatted.get("title", "Untitled"),
        "identifier": formatted.get("identifier"),
        "publication_year": formatted.get("publication_year"),
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
