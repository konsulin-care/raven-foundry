"""Ingestion module - OpenAlex API + PDF processing for Raven.

Environment (from .env):
- OPENALEX_API_KEY: Required. Get from https://openalex.org/
- OPENALEX_API_URL: Optional. Defaults to https://api.openalex.org

Responsibilities:
- Query OpenAlex API
- Download PDFs
- Convert PDF → Markdown (MarkItDown)
- Clean extracted text

Rules:
- Deduplicate using DOI before insertion
- Do not use LLMs in this module
- Keep processing CPU-efficient
- Ensure ingestion integrates cleanly with CLI workflow
"""

import logging
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from raven.config import get_openalex_api_key, get_openalex_api_url
from raven.embeddings import generate_embedding, generate_embeddings_batch
from raven.storage import (
    add_embedding,
    add_paper,
    get_paper_id_by_doi,
)

# Default filters for search results
# Note: Semantic search has limited filter support (no has_doi), so we use separate filters
DEFAULT_FILTERS = "is_oa:true,has_doi:true"  # For keyword search
SEMANTIC_FILTERS = "is_oa:true"  # For semantic search (limited to: is_oa, has_abstract, has_fulltext, etc.)

# Configure logging
logger = logging.getLogger(__name__)


def _create_session_with_retries() -> requests.Session:
    """Create a requests session with retry logic and backoff."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    # Only use HTTPS - never fallback to insecure HTTP
    session.mount("https://", adapter)
    return session


def _get_openalex_base_url() -> str:
    """Get OpenAlex API base URL from config."""
    return get_openalex_api_url()


def normalize_doi(doi: str) -> str:
    """Normalize DOI by stripping URL prefixes and case normalizing."""
    doi = doi.strip().lower()
    if doi.startswith("https://doi.org/"):
        doi = doi.replace("https://doi.org/", "")
    elif doi.startswith("doi:"):
        doi = doi.replace("doi:", "")
    return doi


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


def ingest_paper(db_path: Path, doi: str) -> dict[str, Any] | None:
    """Ingest a paper by DOI from OpenAlex with embedding generation.

    Fetches paper metadata from OpenAlex, stores it in the database,
    generates a semantic embedding from title + abstract, and stores
    the embedding for vector search.

    Args:
        db_path: Path to the SQLite database file.
        doi: DOI of the paper to ingest.

    Returns:
        Dict with paper_id, doi, title, type, and embedding, or None on failure.
    """
    # Get API configuration
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    # Clean DOI
    doi = normalize_doi(doi)

    # Query OpenAlex API (requires doi: prefix)
    url = f"{base_url}/works/doi:{doi}?api_key={api_key}"

    # Use session with retry logic
    session = _create_session_with_retries()
    try:
        response = session.get(url, timeout=30)
    except requests.exceptions.RequestException as e:
        logger.error("Network error fetching paper: %s", e)
        return None

    if response.status_code != 200:
        logger.error("OpenAlex API error: status %s", response.status_code)
        return None

    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        logger.error("Failed to parse response: %s", e)
        return None

    # Extract metadata
    title = data.get("title", "Untitled")
    paper_type = data.get("type", "article")
    abstract = ""
    abstract_inverted = data.get("abstract_inverted_index")
    if abstract_inverted:
        abstract = undo_inverted_index(abstract_inverted)

    # Reconstruct authors list from OpenAlex format
    authors_list = data.get("authorships", [])
    authors = (
        ", ".join(a.get("author", {}).get("display_name", "") for a in authors_list)
        or None
    )

    # Add paper metadata to database
    paper_id = add_paper(
        db_path,
        doi=doi,
        title=title,
        authors=authors,
        abstract=abstract,
        publication_year=data.get("publication_year"),
        venue=data.get("host_venue", {}).get("display_name"),
        openalex_id=data.get("id"),
        paper_type=paper_type,
    )

    # Generate embedding from title + abstract (optional - may fail if vec extension unavailable)
    embedding = None
    try:
        embedding_text = combine_title_abstract(title, abstract)
        embedding = generate_embedding(embedding_text)
        # Store embedding for vector search
        add_embedding(db_path, paper_id, embedding)
    except Exception as e:
        # Log but continue without embedding if extension unavailable
        logger.warning("Failed to generate/store embedding: %s", e)

    return {
        "paper_id": paper_id,
        "doi": doi,
        "title": title,
        "type": paper_type,
        "embedding": embedding,
    }


# Rate limiting for semantic search (1 request per second)
_semantic_last_request_time: float = 0.0


def _rate_limit_semantic() -> None:
    """Apply rate limiting for semantic search."""
    global _semantic_last_request_time
    elapsed = time.time() - _semantic_last_request_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _semantic_last_request_time = time.time()


def _parse_search_query(query: str) -> str:
    """Parse user query to OpenAlex search syntax.

    Handles:
    - Boolean operators (AND, OR, NOT) - passed through
    - Quoted phrases - kept as exact match
    - Wildcards (*, ?) - passed through
    - Fuzzy search (~N) - passed through
    """
    # Normalize whitespace
    query = " ".join(query.split())
    return query


def search_works(
    query: str,
    filter: str | None = None,
    page: int = 1,
    per_page: int = 50,
    sort: str = "relevance_score:desc",
    use_semantic: bool = True,
) -> dict[str, Any]:
    """Search works via OpenAlex API.

    Tries semantic search first, falls back to keyword search on rate limit.

    Args:
        query: Search query string
        filter: Additional OpenAlex filters (e.g., "publication_year:>2020")
        page: Page number (1-indexed)
        per_page: Results per page (max 100)
        sort: Sort order (default: relevance_score:desc)
        use_semantic: If True, try semantic first, then fallback to keyword

    Returns:
        Dict with 'results', 'meta' (pagination info), 'search_type' indicator
    """
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    session = _create_session_with_retries()

    # Try semantic search first if enabled
    if use_semantic:
        try:
            _rate_limit_semantic()

            # Build filters for semantic search (limited supported filters)
            semantic_filters = [SEMANTIC_FILTERS]
            if filter:
                semantic_filters.append(filter)
            combined_semantic_filter = ",".join(semantic_filters)

            url = f"{base_url}/works"
            params: dict[str, Any] = {
                "search.semantic": query,
                "filter": combined_semantic_filter,
                "sort": sort,
                "per_page": min(per_page, 50),  # Semantic max 50
                "page": page,
                "api_key": api_key,
            }

            response = session.get(url, params=params, timeout=30)

            if response.status_code == 200:
                data: dict[str, Any] = response.json()
                data["search_type"] = "semantic"
                return data
            elif response.status_code == 429:
                logger.info("Semantic search rate limited, falling back to keyword")
            else:
                logger.warning(
                    "Semantic search failed: status %s, falling back to keyword",
                    response.status_code,
                )
        except requests.exceptions.RequestException as e:
            logger.warning("Semantic search error: %s, falling back to keyword", e)

    # Fallback to keyword search (use full filters)
    filters = [DEFAULT_FILTERS]
    if filter:
        filters.append(filter)
    combined_filter = ",".join(filters)

    search_type = "keyword"
    url = f"{base_url}/works"
    # Note: params shadows the semantic branch's params but they're in different branches
    keyword_params: dict[str, Any] = {
        "search": _parse_search_query(query),
        "filter": combined_filter,
        "sort": sort,
        "per_page": min(per_page, 100),  # Keyword max 100
        "page": page,
        "api_key": api_key,
    }

    try:
        response = session.get(url, params=keyword_params, timeout=30)

        if response.status_code != 200:
            logger.error("OpenAlex search error: status %s", response.status_code)
            return {"results": [], "meta": {"count": 0}, "search_type": search_type}

        # Note: data shadows the semantic branch's data but they're in different branches
        keyword_data: dict[str, Any] = response.json()
        keyword_data["search_type"] = search_type
        return keyword_data

    except requests.exceptions.RequestException as e:
        logger.error("Network error during search: %s", e)
        return {"results": [], "meta": {"count": 0}, "search_type": search_type}


def search_works_keyword(
    query: str,
    filter: str | None = None,
    page: int = 1,
    per_page: int = 50,
    sort: str = "relevance_score:desc",
) -> dict[str, Any]:
    """Keyword-only search (explicit).

    Args:
        query: Search query string
        filter: Additional OpenAlex filters
        page: Page number
        per_page: Results per page (max 100)
        sort: Sort order

    Returns:
        Dict with 'results', 'meta', 'search_type'='keyword'
    """
    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    filters = [DEFAULT_FILTERS]
    if filter:
        filters.append(filter)
    combined_filter = ",".join(filters)

    session = _create_session_with_retries()
    url = f"{base_url}/works"
    params: dict[str, Any] = {
        "search": _parse_search_query(query),
        "filter": combined_filter,
        "sort": sort,
        "per_page": min(per_page, 100),
        "page": page,
        "api_key": api_key,
    }

    try:
        response = session.get(url, params=params, timeout=30)

        if response.status_code != 200:
            logger.error(
                "OpenAlex keyword search error: status %s", response.status_code
            )
            return {"results": [], "meta": {"count": 0}, "search_type": "keyword"}

        data: dict[str, Any] = response.json()
        data["search_type"] = "keyword"
        return data

    except requests.exceptions.RequestException as e:
        logger.error("Network error during keyword search: %s", e)
        return {"results": [], "meta": {"count": 0}, "search_type": "keyword"}


def search_works_semantic(
    query: str,
    per_page: int = 50,
) -> dict[str, Any]:
    """Semantic-only search (explicit).

    Note: Limited to 1 request per second, max 50 results.

    Args:
        query: Semantic search query
        per_page: Results per page (max 50)

    Returns:
        Dict with 'results', 'meta', 'search_type'='semantic'
    """
    _rate_limit_semantic()

    api_key = get_openalex_api_key()
    base_url = _get_openalex_base_url()

    session = _create_session_with_retries()
    url = f"{base_url}/works"
    params: dict[str, Any] = {
        "search.semantic": query,
        "filter": SEMANTIC_FILTERS,
        "sort": "relevance_score:desc",
        "per_page": min(per_page, 50),
        "api_key": api_key,
    }

    try:
        response = session.get(url, params=params, timeout=30)

        if response.status_code != 200:
            logger.error(
                "OpenAlex semantic search error: status %s", response.status_code
            )
            return {"results": [], "meta": {"count": 0}, "search_type": "semantic"}

        data: dict[str, Any] = response.json()
        data["search_type"] = "semantic"
        return data

    except requests.exceptions.RequestException as e:
        logger.error("Network error during semantic search: %s", e)
        return {"results": [], "meta": {"count": 0}, "search_type": "semantic"}


def undo_inverted_index(inverted_index: dict[str, list[int]]) -> str:
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

    Includes: DOI, Year, Type, Citation, Open Access, Abstract, Embedding Text
    """
    # Reconstruct abstract from inverted index if available
    abstract = ""
    abstract_inverted = work.get("abstract_inverted_index")
    if abstract_inverted:
        abstract = undo_inverted_index(abstract_inverted)

    # Get title for embedding text generation
    title = work.get("title", "Untitled")

    return {
        "doi": work.get("doi"),
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


def ingest_search_results(
    db_path: Path, search_results: dict[str, Any]
) -> list[dict[str, Any]]:
    """Ingest multiple papers from OpenAlex search results.

    Uses batch embedding generation for efficiency. Handles missing abstracts
    gracefully by using title only.

    Args:
        db_path: Path to the SQLite database file.
        search_results: Dict with 'results' list from OpenAlex search API.

    Returns:
        List of ingested paper dicts with paper_id, doi, title, type, embedding.
    """
    results = search_results.get("results", [])
    if not results:
        return []

    # Prepare paper data and embedding texts
    papers_data: list[tuple[dict[str, Any], str]] = []
    embedding_texts: list[str] = []

    for work in results:
        # Format the work result
        formatted = format_search_result(work)

        # Extract needed fields for storage
        doi = formatted.get("doi")
        title = formatted.get("title", "Untitled")
        abstract = formatted.get("abstract", "")

        # Reconstruct authors from authorship data
        authors_list = work.get("authorships", [])
        authors = (
            ", ".join(a.get("author", {}).get("display_name", "") for a in authors_list)
            or None
        )

        paper_info = {
            "doi": doi,
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "publication_year": work.get("publication_year"),
            "venue": work.get("host_venue", {}).get("display_name"),
            "openalex_id": work.get("id"),
            "paper_type": work.get("type", "article"),
        }

        papers_data.append((paper_info, formatted["embedding_text"]))

    # Batch generate embeddings (optional - may fail if vec extension unavailable)
    embeddings = None
    try:
        for _, embedding_text in papers_data:
            embedding_texts.append(embedding_text)
        embeddings = generate_embeddings_batch(embedding_texts)
    except Exception as e:
        logger.warning("Failed to generate embeddings: %s", e)

    # Store papers and embeddings
    ingested = []
    for i, (paper_info, _) in enumerate(papers_data):
        try:
            # Add paper to database
            paper_id = add_paper(db_path, **paper_info)

            # Add embedding if available
            embedding = embeddings[i] if embeddings is not None else None
            if embedding is not None:
                try:
                    add_embedding(db_path, paper_id, embedding)
                except Exception as e:
                    logger.warning("Failed to store embedding: %s", e)

            ingested.append(
                {
                    "paper_id": paper_id,
                    "doi": paper_info["doi"],
                    "title": paper_info["title"],
                    "type": paper_info["paper_type"],
                    "embedding": embedding,
                }
            )
        except ValueError as e:
            # Paper already exists (DOI duplicate) - try to update embedding
            doi = paper_info.get("doi")
            if doi:
                existing_id = get_paper_id_by_doi(db_path, doi)
                if existing_id:
                    # Try to add/update embedding for existing paper
                    embedding = embeddings[i] if embeddings is not None else None
                    if embedding is not None:
                        try:
                            add_embedding(db_path, existing_id, embedding)
                            logger.info("Updated embedding for existing paper: %s", doi)
                        except Exception as emb_err:
                            logger.warning("Failed to update embedding: %s", emb_err)
                    # Still return the existing paper info
                    ingested.append(
                        {
                            "paper_id": existing_id,
                            "doi": doi,
                            "title": paper_info["title"],
                            "type": paper_info["paper_type"],
                            "embedding": embedding,
                        }
                    )
                    continue
            # If we couldn't find/update, log and skip
            logger.info("Skipping duplicate paper: %s", e)
        except Exception as e:
            logger.error("Error ingesting paper %s: %s", paper_info.get("doi"), e)

    return ingested
