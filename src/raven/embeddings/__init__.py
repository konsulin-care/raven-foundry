"""Embeddings module - Semantic embedding generation for Raven.

Model: multilingual-e5-small (384 dimensions)

Rules (from AGENTS.md):
- Do not change embedding dimensionality
- Keep inference CPU-only
- Cache embeddings aggressively
- Ensure compatibility with SQLite vector schema
"""

import shutil
from pathlib import Path
from typing import Optional

from sentence_transformers import SentenceTransformer

# Import from raven.config
from raven.config import _get_data_dir

# Embedding model configuration
EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
EMBEDDING_DIMENSIONS = 384

# Module-level model cache (one-time load per AGENTS.md rules)
_model: Optional[SentenceTransformer] = None


def _get_model_cache_dir() -> Path:
    """Get the model cache directory path.

    Returns:
        Path to the model cache directory (raven/data_dir/model_cache).
    """
    return _get_data_dir() / "model_cache"


def _get_model() -> SentenceTransformer:
    """Load and cache the sentence-transformers model.

    First checks for a local cached model, otherwise downloads from HuggingFace
    and saves to local cache for subsequent use.

    Returns:
        Cached SentenceTransformer model instance.
    """
    global _model
    if _model is None:
        cache_dir = _get_model_cache_dir()

        # Check if local cached model exists
        if cache_dir.exists() and any(cache_dir.iterdir()):
            # Load from local cache (avoids HTTP requests to HuggingFace)
            _model = SentenceTransformer(str(cache_dir))
        else:
            # Load from HuggingFace and save to local cache
            # Create cache directory if it doesn't exist
            cache_dir.mkdir(parents=True, exist_ok=True)
            _model = SentenceTransformer(EMBEDDING_MODEL)
            _model.save_pretrained(str(cache_dir))

    return _model


def get_model_cache_size() -> Optional[int]:
    """Get the size of the cached model in bytes.

    Returns:
        Size of the cached model in bytes, or None if cache doesn't exist.
    """
    cache_dir = _get_model_cache_dir()
    if not cache_dir.exists():
        return None

    total_size = 0
    for item in cache_dir.rglob("*"):
        if item.is_file():
            total_size += item.stat().st_size

    return total_size


def clean_model_cache() -> None:
    """Delete the model cache directory."""
    cache_dir = _get_model_cache_dir()
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    # Reset in-memory model so next call re-downloads to cache
    global _model
    _model = None


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
