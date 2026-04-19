"""Ingestion pipeline - orchestrates paper ingestion from OpenAlex to storage.

This module handles the core ingestion logic:
- Manage paper deduplication (by identifier)
- Generate and store embeddings
- Handle batch processing

Rules:
- Deduplicate using identifier before insertion
- Do not use LLMs in this module
"""

import logging
from pathlib import Path
from typing import Any

from raven.embeddings import generate_embedding, generate_embeddings_batch
from raven.ingestion.api import fetch_work
from raven.ingestion.identifier import normalize_identifier
from raven.ingestion.metadata import extract_paper_metadata, prepare_paper_info
from raven.ingestion.text import combine_title_abstract
from raven.storage import (
    add_embedding,
    add_paper,
    get_embedding_exists,
    get_paper_id_by_identifier,
    update_paper,
)

logger = logging.getLogger(__name__)


def _get_existing_paper_info(
    db_path: Path, identifier: str | None
) -> tuple[int | None, bool]:
    """Check if identifier exists in database and whether it has an embedding."""
    existing_id = get_paper_id_by_identifier(db_path, identifier)
    if existing_id is None:
        return None, False
    has_embedding = get_embedding_exists(db_path, existing_id)
    return existing_id, has_embedding


def _handle_existing_paper(
    db_path: Path,
    identifier: str | None,
    paper_info: dict[str, Any],
    existing_id: int,
    has_embedding: bool,
) -> int | None:
    """Handle case where identifier already exists in database."""
    if has_embedding:
        logger.info(
            "Paper with identifier %s already fully stored (paper + embedding)",
            identifier,
        )
        return None

    logger.info(
        "Paper with identifier %s exists without embedding, updating and generating embedding",
        identifier,
    )
    sanitized_paper_info = {k: v for k, v in paper_info.items() if k != "identifier"}
    update_paper(db_path, existing_id, **sanitized_paper_info)
    return existing_id


def _store_paper_with_embedding(
    db_path: Path,
    paper_info: dict[str, Any],
    embedding: list[float] | None,
    embedding_text: str | None = None,
) -> int:
    """Store paper and its embedding in database."""
    identifier = paper_info.get("identifier")

    paper_id = None
    if identifier:
        existing_id, has_embedding = _get_existing_paper_info(db_path, identifier)

        if existing_id is not None:
            paper_id = _handle_existing_paper(
                db_path, identifier, paper_info, existing_id, has_embedding
            )
            if paper_id is None:
                return existing_id
        else:
            logger.info("Adding new paper with identifier %s", identifier)
            paper_id = add_paper(db_path, **paper_info)
    else:
        logger.info("Adding new paper with identifier N/A")
        paper_id = add_paper(db_path, **paper_info)

    if embedding is not None and embedding_text is not None:
        try:
            add_embedding(
                db_path, paper_id, embedding, embedding_text, content_type="title"
            )
        except Exception as e:
            logger.warning("Failed to store embedding: %s", e)

    return paper_id


def ingest_paper(db_path: Path, identifier: str) -> dict[str, Any] | None:
    """Ingest a paper by identifier from OpenAlex with embedding generation."""
    normalized = normalize_identifier(identifier)
    work = fetch_work(normalized)
    if work is None:
        return None

    metadata = extract_paper_metadata(work)
    final_identifier = metadata["identifier"]
    title = metadata["title"]
    paper_type = metadata["paper_type"]
    abstract = metadata["abstract"]

    paper_info = {
        "identifier": final_identifier,
        "title": title,
        "authors": metadata["authors"],
        "authors_data": metadata.get("authors_data"),
        "abstract": abstract,
        "year": metadata.get("year"),
        "source": metadata.get("source"),
        "paper_type": paper_type,
    }

    embedding = None
    embedding_text = None
    try:
        embedding_text = combine_title_abstract(title, abstract)
        embedding = generate_embedding(embedding_text)
    except Exception as e:
        logger.warning("Failed to generate embedding: %s", e)

    paper_id = _store_paper_with_embedding(
        db_path, paper_info, embedding, embedding_text
    )

    return {
        "paper_id": paper_id,
        "identifier": final_identifier,
        "title": title,
        "type": paper_type,
        "embedding": embedding,
    }


def _generate_embeddings_safe(
    papers_data: list[tuple[dict[str, Any], str | None]],
) -> list[list[float] | None] | None:
    """Generate embeddings aligned to papers_data (None preserved at same positions)."""
    valid_texts, valid_indices = [], []
    for i, (_, text) in enumerate(papers_data):
        if text is not None:
            valid_texts.append(text)
            valid_indices.append(i)

    if not valid_texts:
        return None

    try:
        generated = generate_embeddings_batch(valid_texts)
        embeddings_aligned: list[list[float] | None] = [None] * len(papers_data)
        for idx, emb in zip(valid_indices, generated):
            embeddings_aligned[idx] = emb
        return embeddings_aligned
    except Exception as e:
        logger.warning("Failed to generate embeddings: %s", e)
        return None


def _store_and_build_results(
    db_path: Path,
    papers_data: list[tuple[dict[str, Any], str | None]],
    embeddings: list[list[float] | None] | None,
) -> list[dict[str, Any]]:
    """Store each paper and build results list."""
    ingested = []
    for i, (paper_info, embedding_text) in enumerate(papers_data):
        emb = embeddings[i] if embeddings else None
        paper_id = _store_paper_with_embedding(db_path, paper_info, emb, embedding_text)
        ingested.append(
            {
                "paper_id": paper_id,
                "identifier": paper_info["identifier"],
                "title": paper_info["title"],
                "type": paper_info["paper_type"],
                "embedding": emb,
            }
        )
    return ingested


def ingest_search_results(
    db_path: Path, search_results: dict[str, Any]
) -> list[dict[str, Any]]:
    """Ingest multiple papers from OpenAlex search results."""
    results = search_results.get("results", [])
    if not results:
        return []
    papers_data: list[tuple[dict[str, Any], str | None]] = [
        prepare_paper_info(w) for w in results
    ]
    embeddings = _generate_embeddings_safe(papers_data)
    return _store_and_build_results(db_path, papers_data, embeddings)
