"""Unit tests for raven.embeddings module.

Run with: pytest tests/test_embeddings.py -v
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Need to import the module to reset the cached model between tests
import raven.embeddings
from raven.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    _get_model,
    generate_embedding,
    generate_embeddings_batch,
)


class TestEmbeddingsConstants:
    """Tests for embeddings module constants."""

    def test_embedding_model_name(self):
        """Verify correct model name is configured."""
        assert EMBEDDING_MODEL == "intfloat/multilingual-e5-small"

    def test_embedding_dimensions(self):
        """Verify 384-dimensional embeddings."""
        assert EMBEDDING_DIMENSIONS == 384


class TestGenerateEmbedding:
    """Tests for generate_embedding function."""

    def test_generate_embedding_returns_list(self):
        """generate_embedding returns a list of floats."""
        # Mock the model to avoid downloading
        mock_embedding = np.array([0.1] * EMBEDDING_DIMENSIONS)

        with patch("raven.embeddings._get_model") as mock_get_model:
            mock_model = mock_get_model.return_value
            mock_model.encode.return_value = mock_embedding

            result = generate_embedding("test text")

            assert isinstance(result, list)
            assert len(result) == EMBEDDING_DIMENSIONS

    def test_generate_embedding_empty_text_raises(self):
        """generate_embedding raises ValueError for empty text."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            generate_embedding("")

    def test_generate_embedding_whitespace_only_raises(self):
        """generate_embedding raises ValueError for whitespace-only text."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            generate_embedding("   ")

    def test_generate_embedding_none_raises(self):
        """generate_embedding raises ValueError for None input."""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            generate_embedding(None)  # type: ignore

    def test_generate_embedding_calls_model(self):
        """generate_embedding calls model.encode with normalize."""
        with patch("raven.embeddings._get_model") as mock_get_model:
            mock_model = mock_get_model.return_value
            mock_model.encode.return_value = np.array([0.1] * EMBEDDING_DIMENSIONS)

            generate_embedding("test text")

            mock_model.encode.assert_called_once_with(
                "test text", normalize_embeddings=True
            )


class TestGenerateEmbeddingsBatch:
    """Tests for generate_embeddings_batch function."""

    def test_generate_embeddings_batch_returns_list(self):
        """generate_embeddings_batch returns list of lists."""
        mock_embeddings = np.array(
            [
                [0.1] * EMBEDDING_DIMENSIONS,
                [0.2] * EMBEDDING_DIMENSIONS,
            ]
        )

        with patch("raven.embeddings._get_model") as mock_get_model:
            mock_model = mock_get_model.return_value
            mock_model.encode.return_value = mock_embeddings

            result = generate_embeddings_batch(["text 1", "text 2"])

            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(emb, list) for emb in result)

    def test_generate_embeddings_batch_empty_list_raises(self):
        """generate_embeddings_batch raises ValueError for empty list."""
        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            generate_embeddings_batch([])

    def test_generate_embeddings_batch_single_text(self):
        """generate_embeddings_batch handles single text in list."""
        mock_embeddings = np.array([[0.1] * EMBEDDING_DIMENSIONS])

        with patch("raven.embeddings._get_model") as mock_get_model:
            mock_model = mock_get_model.return_value
            mock_model.encode.return_value = mock_embeddings

            result = generate_embeddings_batch(["single text"])

            assert len(result) == 1

    def test_generate_embeddings_batch_calls_model(self):
        """generate_embeddings_batch calls model.encode with normalize."""
        with patch("raven.embeddings._get_model") as mock_get_model:
            mock_model = mock_get_model.return_value
            mock_model.encode.return_value = np.array([[0.1] * EMBEDDING_DIMENSIONS])

            generate_embeddings_batch(["text"])

            mock_model.encode.assert_called_once_with(
                ["text"], normalize_embeddings=True
            )

    def test_generate_embeddings_batch_filters_empty(self):
        """Batch filters empty strings and replaces with placeholder."""
        # Mock returns 3 embeddings for the 3 input texts

        mock_embeddings = np.array(
            [
                [0.1] * EMBEDDING_DIMENSIONS,
                [0.2] * EMBEDDING_DIMENSIONS,
                [0.3] * EMBEDDING_DIMENSIONS,
            ]
        )

        with patch("raven.embeddings._get_model") as mock_get_model:
            mock_model = mock_get_model.return_value
            mock_model.encode.return_value = mock_embeddings

            # Empty/whitespace strings should be replaced with placeholder
            # and all 3 should produce embeddings
            result = generate_embeddings_batch(["valid text", "", " "])

            # Should return results for all 3 inputs
            assert len(result) == 3


class TestGetModel:
    """Tests for _get_model function and model caching."""

    def test_get_model_returns_sentence_transformer(self):
        """_get_model returns a SentenceTransformer instance."""
        with patch("raven.embeddings.SentenceTransformer") as mock_st:
            mock_instance = MagicMock()
            mock_st.return_value = mock_instance

            # Reset cached model to ensure fresh load
            raven.embeddings._model = None

            result = _get_model()

            mock_st.assert_called_once_with(EMBEDDING_MODEL)
            assert result is mock_instance

    def test_get_model_caches_model(self):
        """_get_model caches the model and returns same instance on subsequent calls."""
        with patch("raven.embeddings.SentenceTransformer") as mock_st:
            mock_instance = MagicMock()
            mock_st.return_value = mock_instance

            # Reset cached model to ensure fresh start
            raven.embeddings._model = None

            # First call - should create new model
            result1 = _get_model()

            # Second call - should return cached model (not create new)
            result2 = _get_model()

            # Should return the same instance
            assert result1 is result2
            assert result2 is mock_instance

            # SentenceTransformer should only be called once (caching works)
            assert mock_st.call_count == 1

    def test_get_model_uses_correct_model_name(self):
        """_get_model loads the correct embedder model."""
        with patch("raven.embeddings.SentenceTransformer") as mock_st:
            mock_instance = MagicMock()
            mock_st.return_value = mock_instance

            raven.embeddings._model = None

            _get_model()

            # Verify the model name matches the constant
            mock_st.assert_called_once_with(EMBEDDING_MODEL)
