"""Unit tests for raven.embeddings module.

Run with: pytest tests/test_embeddings.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Need to import the module to reset the cached model between tests
import raven.embeddings
from raven.embeddings import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    _get_model,
    _get_model_cache_dir,
    clean_model_cache,
    generate_embedding,
    generate_embeddings_batch,
    get_model_cache_size,
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
        with (
            patch("raven.embeddings.SentenceTransformer") as mock_st,
            patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir,
        ):
            mock_instance = MagicMock()
            mock_st.return_value = mock_instance

            # Return a non-existent cache dir so it downloads from HF
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_cache_dir.return_value = mock_cache_path

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
        with (
            patch("raven.embeddings.SentenceTransformer") as mock_st,
            patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir,
        ):
            mock_instance = MagicMock()
            mock_st.return_value = mock_instance

            # Return a non-existent cache dir so it downloads from HF
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_cache_dir.return_value = mock_cache_path

            raven.embeddings._model = None

            _get_model()

            # Verify the model name matches the constant
            mock_st.assert_called_once_with(EMBEDDING_MODEL)

    def test_get_model_loads_from_local_cache(self):
        """_get_model loads from local cache when available."""
        with (
            patch("raven.embeddings.SentenceTransformer") as mock_st,
            patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir,
        ):
            mock_instance = MagicMock()
            mock_st.return_value = mock_instance

            # Create a mock cache directory with files
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = True
            # Make iterdir return a non-empty list (truthy for any())
            mock_cache_path.iterdir.return_value = [MagicMock(), MagicMock()]
            mock_cache_dir.return_value = mock_cache_path

            # Reset cached model to ensure fresh load
            raven.embeddings._model = None

            _get_model()

            # Should load from local path, not from HuggingFace
            mock_st.assert_called_once_with(str(mock_cache_path))

    def test_get_model_downloads_when_cache_empty(self):
        """_get_model downloads from HuggingFace when cache doesn't exist."""
        with (
            patch("raven.embeddings.SentenceTransformer") as mock_st,
            patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir,
        ):
            mock_instance = MagicMock()
            mock_st.return_value = mock_instance

            # Create a mock cache directory that doesn't exist
            mock_cache_path = MagicMock()
            mock_cache_path.exists.return_value = False
            mock_cache_dir.return_value = mock_cache_path

            # Reset cached model to ensure fresh load
            raven.embeddings._model = None

            _get_model()

            # Should load from HuggingFace and save to cache
            mock_st.assert_called_with(EMBEDDING_MODEL)
            mock_instance.save_pretrained.assert_called_once_with(str(mock_cache_path))


class TestModelCache:
    """Tests for model cache functions."""

    def test_get_model_cache_dir_returns_path(self):
        """_get_model_cache_dir returns a Path."""
        result = _get_model_cache_dir()
        assert isinstance(result, Path)
        assert "model_cache" in str(result)

    def test_get_model_cache_size_returns_none_when_no_cache(self):
        """get_model_cache_size returns None when no cache exists."""
        with patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_cache_dir.return_value = mock_path

            result = get_model_cache_size()

            assert result is None

    def test_get_model_cache_size_returns_bytes(self):
        """get_model_cache_size returns size in bytes."""
        with patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.rglob.return_value = [
                MagicMock(is_file=lambda: True, stat=lambda: MagicMock(st_size=100)),
                MagicMock(is_file=lambda: True, stat=lambda: MagicMock(st_size=200)),
            ]
            mock_cache_dir.return_value = mock_path

            result = get_model_cache_size()

            assert result == 300

    def test_clean_model_cache_removes_directory(self):
        """clean_model_cache removes the cache directory."""
        with (
            patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir,
            patch("raven.embeddings.shutil.rmtree") as mock_rmtree,
        ):
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_cache_dir.return_value = mock_path

            clean_model_cache()

            mock_rmtree.assert_called_once_with(mock_path)

    def test_clean_model_cache_handles_missing_directory(self):
        """clean_model_cache handles missing directory gracefully."""
        with (
            patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir,
            patch("raven.embeddings.shutil.rmtree") as mock_rmtree,
        ):
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_cache_dir.return_value = mock_path

            clean_model_cache()

            mock_rmtree.assert_not_called()

    def test_clean_model_cache_resets_in_memory_model(self):
        """clean_model_cache resets the in-memory model."""
        with (
            patch("raven.embeddings._get_model_cache_dir") as mock_cache_dir,
            patch("raven.embeddings.shutil.rmtree"),
        ):
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_cache_dir.return_value = mock_path

            # Simulate having a model loaded in memory
            raven.embeddings._model = MagicMock()

            clean_model_cache()

            # Model should be reset to None
            assert raven.embeddings._model is None
