"""Embeddings module - Semantic embedding generation for Raven.

Model: multilingual-e5-small (384 dimensions)

Rules (from AGENTS.md):
- Do not change embedding dimensionality
- Keep inference CPU-only
- Cache embeddings aggressively
- Ensure compatibility with SQLite vector schema
"""

# Embedding model configuration
EMBEDDING_MODEL = "multilingual-e5-small"
EMBEDDING_DIMENSIONS = 384


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for text using the configured model."""
    # TODO: Implement with sentence-transformers
    # CPU-only inference
    # Aggressive caching
    raise NotImplementedError("Embedding generation not yet implemented")


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts."""
    # TODO: Batch processing as per AGENTS.md rules
    raise NotImplementedError("Batch embedding not yet implemented")
