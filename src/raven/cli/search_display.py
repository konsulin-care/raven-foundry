"""Display helpers for search results."""

import json
from typing import Any

import click


def format_json_result(result: dict[str, Any]) -> dict[str, Any]:
    """Format a search result for JSON output.

    Args:
        result: Normalized search result.

    Returns:
        Dict with fields for JSON output.
    """
    output = {
        "title": result.get("title"),
        "identifier": result.get("identifier"),
        "year": result.get("year"),
        "type": result.get("type"),
        "abstract": result.get("abstract"),
        "source": result.get("source"),
        "ingested": result.get("ingested", False),
        "relevance_score": round(result.get("relevance_score", 0), 3),
    }
    # Add optional fields if present
    if result.get("authors"):
        output["authors"] = result.get("authors")
    if result.get("cited_by_count"):
        output["cited_by_count"] = result.get("cited_by_count")
    if result.get("open_access"):
        output["open_access"] = result.get("open_access")
    return output


def display_json(
    results: list[dict[str, Any]], closest_info: dict[str, Any] | None = None
) -> None:
    """Display results as JSON (one per line).

    Args:
        results: List of search results.
        closest_info: Info about closest match if no results within threshold.
    """
    if not results:
        if closest_info:
            click.echo(
                f"# No results within threshold. Closest: {closest_info['title']}"
            )
            click.echo(
                f"# Distance: {closest_info['distance']:.3f} (relevance: {closest_info['relevance']:.3f})"
            )
        else:
            click.echo("# No results found")

    for result in results:
        output = format_json_result(result)
        click.echo(json.dumps(output))


def _display_no_results(
    closest_info: dict[str, Any] | None,
    max_distance: float,
) -> None:
    """Display message when no results found."""
    if closest_info:
        click.echo(f"No results found within threshold (distance < {max_distance}).")
        click.echo(f"Closest match: {closest_info['title']}")
        click.echo(
            f"Distance: {closest_info['distance']:.3f} (relevance: {closest_info['relevance']:.3f})"
        )
        if closest_info.get("identifier"):
            click.echo(f"Identifier: {closest_info['identifier']}")
    else:
        click.echo("No results found.")


def _display_single_result(index: int, paper: dict[str, Any]) -> None:
    """Display a single search result."""
    title = paper.get("title", "Untitled")
    click.echo(f"{index}. {title}")

    if identifier := paper.get("identifier"):
        click.echo(f"   Identifier: {identifier}")
    if year := paper.get("year"):
        click.echo(f"   Year: {year}")
    click.echo(f"   Type: {paper.get('type', 'unknown')}")
    click.echo(f"   Source: {paper.get('source', 'unknown')}")

    ingested = "Yes" if paper.get("ingested") else "No"
    click.echo(f"   Ingested: {ingested}")

    if score := paper.get("relevance_score"):
        click.echo(f"   Relevance: {score:.3f}")

    if abstract := paper.get("abstract"):
        preview = abstract[:300] + ("..." if len(abstract) > 300 else "")
        click.echo(f"   Abstract: {preview}")
    click.echo("---")


def display_text(
    results: list[dict[str, Any]],
    total: int,
    page: int,
    per_page: int,
    closest_info: dict[str, Any] | None = None,
    max_distance: float = 0.1,
) -> None:
    """Display results in text format.

    Args:
        results: List of search results.
        total: Total number of results.
        page: Current page number.
        per_page: Results per page.
        closest_info: Info about closest match if no results within threshold.
        max_distance: Distance threshold for filtering.
    """
    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0

    if not results:
        _display_no_results(closest_info, max_distance)
        return

    for i, paper in enumerate(results, 1):
        _display_single_result(i, paper)

    click.echo(
        f"Showing {len(results)} of {total} results (page {page} of ~{total_pages})"
    )
