"""Embeddings module - Semantic embedding generation for Raven.

Model: multilingual-e5-small (384 dimensions)

Rules (from AGENTS.md):
- Do not change embedding dimensionality
- Keep inference CPU-only
- Cache embeddings aggressively
- Ensure compatibility with SQLite vector schema
"""

from typing import Optional

from sentence_transformers import SentenceTransformer

# Embedding model configuration
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSIONS = 384

# Module-level model cache (one-time load per AGENTS.md rules)
_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Load and cache the sentence-transformers model.

    Returns:
        Cached SentenceTransformer model instance.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate embedding for a single text using the configured model.

    Uses normalize_embeddings=True for cosine similarity compatibility.

    Args:
        text: Input text to embed.

    Returns:
        List of 384 float values representing the text embedding.

    Raises:
        ValueError: If text is empty or None.
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty or whitespace only")

    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)

    # Convert numpy array to list of floats
    return embedding.tolist()  # type: ignore[no-any-return]


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for multiple texts in a single batch.

    Uses batch processing with normalize_embeddings=True for cosine similarity.

    Args:
        texts: List of input texts to embed.

    Returns:
        List of embeddings, each a list of 384 floats.

    Raises:
        ValueError: If texts list is empty.
    """
    if not texts:
        raise ValueError("Texts list cannot be empty")

    # Filter out empty/whitespace texts - model.encode would produce zero vectors
    # but we filter to avoid returning meaningless embeddings
    valid_texts = [t.strip() if t else "" for t in texts]
    # Replace empty/whitespace-only with placeholder (model will handle gracefully)
    valid_texts = [t if t else " " for t in valid_texts]

    model = _get_model()
    embeddings = model.encode(valid_texts, normalize_embeddings=True)

    # Convert numpy array to list of lists
    return embeddings.tolist()  # type: ignore[no-any-return]
