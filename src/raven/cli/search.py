"""Search command for Raven CLI."""

from pathlib import Path
from typing import Optional

import click

from raven.cli.resolver import resolve_db_path
from raven.cli.search_orchestrator import search_with_fallback
from raven.ingestion import DEFAULT_SORT_ORDER


@click.command()
@click.argument("query")
@click.option(
    "--db",
    "-d",
    type=click.Path(path_type=Path, dir_okay=False),
    default=None,
    help="Path to the database file (overrides env-derived path)",
)
@click.option(
    "--env",
    "-e",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=None,
    help="Path to .env file",
)
@click.option(
    "--filter",
    "-f",
    "filter_str",
    default=None,
    help="Additional OpenAlex filters (e.g., publication_year:>2020,type:article)",
)
@click.option(
    "--page",
    "-p",
    default=1,
    type=int,
    help="Page number for pagination",
)
@click.option(
    "--per-page",
    default=50,
    type=int,
    help="Results per page (max 100 for keyword, 50 for semantic)",
)
@click.option(
    "--sort",
    default=DEFAULT_SORT_ORDER,
    help="Sort order in OpenAlex format (e.g., 'publication_year:desc,relevance_score:desc')",
)
@click.option(
    "--local",
    is_flag=True,
    default=False,
    help="Search local database only (no OpenAlex)",
)
@click.option(
    "--local-keyword",
    is_flag=True,
    default=False,
    help="Use keyword search (LIKE matching) instead of vector search for local search",
)
@click.option(
    "--text",
    is_flag=True,
    default=False,
    help="Display results as text instead of JSON",
)
@click.option(
    "--semantic/--keyword",
    "use_semantic",
    default=True,
    help="Search mode: semantic (default) or keyword only",
)
def search(
    query: str,
    db: Optional[Path],
    env: Optional[Path],
    filter_str: Optional[str],
    page: int,
    per_page: int,
    sort: str,
    use_semantic: bool,
    local: bool,
    local_keyword: bool,
    text: bool,
) -> None:
    """Search publications by query string.

    Searches OpenAlex by default. Use --local for local database search.

    Examples:
        raven search "machine learning"
            → search OpenAlex (default)
        raven search "machine learning" --local
            → search local database
        raven search "machine learning" --text
            → display as formatted text
        raven search "machine learning" --filter "publication_year:>2020" --page 2
    """
    db_path = resolve_db_path(env, db)
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True, exist_ok=True)
    search_with_fallback(
        db_path=db_path,
        query=query,
        local=local,
        keyword=local_keyword,
        use_semantic=use_semantic,
        filter_str=filter_str,
        page=page,
        per_page=per_page,
        sort=sort,
        text_output=text,
    )
