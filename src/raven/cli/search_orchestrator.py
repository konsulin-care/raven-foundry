"""Search orchestrator with fallback logic for Raven CLI."""

import logging
from pathlib import Path
from typing import Any

import click

from raven.embeddings import generate_embedding
from raven.ingestion import format_search_result, search_works
from raven.storage.embedding import search_by_embedding
from raven.storage.paper import search_papers

logger = logging.getLogger(__name__)


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
) -> None:
    """Search with fallback based on flags.

    Behavior chains:
    - raven search "query" → local vector → OpenAlex semantic fallback
    - raven search "query" --keyword → local keyword → OpenAlex keyword fallback
    - raven search "query" --local → local vector only (no fallback)
    - raven search "query" --local --keyword → local keyword only
    """
    if local:
        _search_local_only(db_path, query, keyword)
    elif keyword:
        _try_local_keyword_then_openalex(
            db_path, query, filter_str, page, per_page, sort
        )
    else:
        _try_local_vector_then_openalex(
            db_path, query, filter_str, page, per_page, sort
        )


def _try_local_vector_then_openalex(
    db_path: Path,
    query: str,
    filter_str: str | None,
    page: int,
    per_page: int,
    sort: str,
) -> None:
    """Try local vector search, fallback to OpenAlex semantic."""
    embedding = generate_embedding(query)
    results = search_by_embedding(db_path, embedding)

    if results:
        _display_local_results(results, show_relevance=True)
        return

    click.echo("No local results. Falling back to OpenAlex semantic search...")
    _search_openalex(query, filter_str, page, per_page, sort, use_semantic=True)


def _try_local_keyword_then_openalex(
    db_path: Path,
    query: str,
    filter_str: str | None,
    page: int,
    per_page: int,
    sort: str,
) -> None:
    """Try local keyword search, fallback to OpenAlex keyword."""
    results = search_papers(db_path, query)

    if results:
        _display_local_results(results, show_relevance=False)
        return

    click.echo("No local results. Falling back to OpenAlex keyword search...")
    _search_openalex(query, filter_str, page, per_page, sort, use_semantic=False)


def _search_local_only(db_path: Path, query: str, keyword: bool) -> None:
    """Search local database only (no fallback)."""
    if keyword:
        results = search_papers(db_path, query)
    else:
        embedding = generate_embedding(query)
        results = search_by_embedding(db_path, embedding)

    _display_local_results(results, show_relevance=not keyword)


def _display_local_results(results: list[dict[str, Any]], show_relevance: bool) -> None:
    """Display local results in OpenAlex format, omitting missing fields."""
    if not results:
        click.echo("No results found in local database.")
        return

    for i, paper in enumerate(results, 1):
        title = paper.get("title", "Untitled")
        click.echo(f"{i}. {title}")

        if identifier := paper.get("identifier"):
            click.echo(f"   Identifier: {identifier}")
        if year := paper.get("publication_year"):
            click.echo(f"   Year: {year}")
        click.echo(f"   Type: {paper.get('type', 'unknown')}")

        if show_relevance and (score := paper.get("relevance_score")):
            click.echo(f"   Relevance: {score:.3f}")

        if abstract := paper.get("abstract"):
            preview = abstract[:300] + ("..." if len(abstract) > 300 else "")
            click.echo(f"   Abstract: {preview}")
        click.echo("---")


def _search_openalex(
    query: str,
    filter_str: str | None,
    page: int,
    per_page: int,
    sort: str,
    use_semantic: bool,
) -> None:
    """Search OpenAlex and display results."""
    result_data = search_works(
        query=query,
        filter_str=filter_str,
        page=page,
        per_page=per_page,
        sort=sort,
        use_semantic=use_semantic,
    )

    results = result_data.get("results", [])
    meta = result_data.get("meta", {})
    search_type = result_data.get("search_type", "unknown")

    if not results:
        click.echo("No results found.")
        return

    click.echo(f"Search type: {search_type}")
    click.echo(f"Total results: {meta.get('count', 'unknown')}")
    click.echo(f"Page: {page} of ~{(meta.get('count', 0) // per_page) + 1}")
    click.echo("---")

    for i, work in enumerate(results, 1):
        formatted = format_search_result(work)
        _print_openalex_result(i, formatted)

    click.echo("To ingest a paper, run: raven ingest <identifier>")
    click.echo("Examples:")
    click.echo("  raven ingest 10.5281/zenodo.18201069")
    click.echo("  raven ingest W7119934875")


def _print_openalex_result(index: int, formatted: dict[str, Any]) -> None:
    """Print a single formatted OpenAlex result."""
    click.echo(f"{index}. {formatted['title']}")

    if formatted.get("identifier"):
        click.echo(f"   Identifier: {formatted['identifier']}")
    if formatted.get("publication_year"):
        click.echo(f"   Year: {formatted['publication_year']}")

    click.echo(f"   Type: {formatted['type']}")

    if formatted.get("cited_by_count"):
        click.echo(f"   Citations: {formatted['cited_by_count']}")
    if formatted.get("open_access"):
        click.echo("   Open Access: Yes")
    if formatted.get("relevance_score"):
        click.echo(f"   Relevance: {formatted['relevance_score']:.3f}")
    if formatted.get("abstract"):
        preview = formatted["abstract"][:300] + (
            "..." if len(formatted["abstract"]) > 300 else ""
        )
        click.echo(f"   Abstract: {preview}")
    click.echo("---")
