"""Search orchestrator for Raven CLI - OpenAlex default with local option."""

import logging
from pathlib import Path
from typing import Any

from raven.cli.search_db import check_batch_ingested
from raven.cli.search_normalize import (
    normalize_local_keyword,
    normalize_local_result,
    normalize_local_vector,
    normalize_openalex,
)
from raven.embeddings import generate_embedding
from raven.ingestion import format_search_result, search_works
from raven.storage.embedding import search_by_embedding

logger = logging.getLogger(__name__)

LOCAL_MAX_RESULTS = 10
LOCAL_MAX_DISTANCE = 0.1

# Re-export for backward compatibility
__all__ = [
    # Constants
    "LOCAL_MAX_RESULTS",
    "LOCAL_MAX_DISTANCE",
    # Normalize functions (with underscore prefix for backward compat)
    "_normalize_local_result",
    "_normalize_local_vector",
    "_normalize_local_keyword",
    "_normalize_openalex",
    # Internal functions
    "_fetch_local_results",
    "_fetch_openalex_results",
    "_search_local_only",
    "_search_openalex",
    "search_with_fallback",
]


# Backward compatibility aliases
_normalize_local_result = normalize_local_result
_normalize_local_vector = normalize_local_vector
_normalize_local_keyword = normalize_local_keyword
_normalize_openalex = normalize_openalex


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
            db_path, query, filter_str, page, per_page, use_semantic, sort, text_output
        )


def _search_local_only(
    db_path: Path, query: str, keyword: bool, text_output: bool
) -> None:
    """Search local database only."""
    from raven.cli.search_display import display_json, display_text
    from raven.storage.paper import search_papers

    if keyword:
        results = search_papers(db_path, query)
        normalized = [normalize_local_keyword(r) for r in results]
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
    use_semantic: bool,
    sort: str,
    text_output: bool,
) -> None:
    """Search OpenAlex and check ingestion status."""
    from raven.cli.search_display import display_json, display_text

    openalex_results, total = _fetch_openalex_results(
        query, filter_str, page, per_page, use_semantic, sort
    )

    # Batch check ingestion status (single SQL query)
    ingested_ids = check_batch_ingested(db_path, openalex_results)

    # Mark ingested status
    for r in openalex_results:
        identifier = r.get("identifier")
        r["ingested"] = identifier is not None and identifier.lower() in ingested_ids

    # Apply local pagination (slice relative to overscanned results)
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
    from raven.storage.paper import search_papers

    if keyword:
        results = search_papers(db_path, query)
        return ([normalize_local_keyword(r) for r in results], None)

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

    return ([normalize_local_vector(r) for r in filtered], closest_info)


def _fetch_openalex_results(
    query: str,
    filter_str: str | None,
    page: int,
    per_page: int,
    use_semantic: bool,
    sort: str,
) -> tuple[list[dict[str, Any]], int]:
    """Fetch OpenAlex results.

    Returns:
        Tuple of (normalized results, total count from API)
    """
    oversfetch_per_page = max(per_page * 2, 100)
    result_data = search_works(
        query=query,
        filter_str=filter_str,
        page=1,
        per_page=oversfetch_per_page,
        sort=sort,
        use_semantic=use_semantic,
    )
    results = result_data.get("results", [])
    total = result_data.get("meta", {}).get("count", 0)
    normalized = [normalize_openalex(r, format_search_result(r)) for r in results]
    return (normalized, total)
