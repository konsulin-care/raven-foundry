"""Unit tests for lazy import helper in raven.embeddings module.

Run with: pytest tests/unit/test_embeddings/test_lazy_import.py -v
"""

from unittest.mock import MagicMock, patch

import pytest


class TestLazyImport:
    """Tests for _lazy_get_model interactive logging."""

    @pytest.fixture(autouse=True)
    def reset_module_state(self):
        """Reset module state before each test."""
        import raven.embeddings as embeddings_module

        # Save original state
        original_model = embeddings_module._model
        original_loaded = embeddings_module._model_loaded

        # Reset for testing
        embeddings_module._model = None
        embeddings_module._model_loaded = False

        yield

        # Restore original state
        embeddings_module._model = original_model
        embeddings_module._model_loaded = original_loaded

    def test_lazy_get_model_prints_loading_message(self, reset_module_state, capsys):
        """_lazy_get_model prints loading message on first call."""
        import raven.embeddings as embeddings_module

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)

        with patch.object(embeddings_module, "_get_model", return_value=mock_model):
            embeddings_module._lazy_get_model()

        captured = capsys.readouterr()
        assert "Loading sentence_transformers..." in captured.out

    def test_lazy_get_model_prints_loaded_message(self, reset_module_state, capsys):
        """_lazy_get_model prints loaded message after first call."""
        import raven.embeddings as embeddings_module

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)

        with patch.object(embeddings_module, "_get_model", return_value=mock_model):
            embeddings_module._lazy_get_model()

        captured = capsys.readouterr()
        assert "sentence_transformers loaded." in captured.out

    def test_lazy_get_model_no_duplicate_messages(self, reset_module_state, capsys):
        """_lazy_get_model does not print messages on subsequent calls."""
        import raven.embeddings as embeddings_module

        mock_model = MagicMock()
        mock_model.encode.return_value = MagicMock(tolist=lambda: [0.0] * 384)

        with patch.object(embeddings_module, "_get_model", return_value=mock_model):
            # First call - should print both messages
            embeddings_module._lazy_get_model()
            # Second call - should not print any messages
            embeddings_module._lazy_get_model()

        captured = capsys.readouterr()
        # Should have exactly 2 lines (loading + loaded)
        lines = [line for line in captured.out.split("\n") if line.strip()]
        assert len(lines) == 2

    def test_generate_embedding_triggers_lazy_load(self, reset_module_state, capsys):
        """generate_embedding triggers lazy loading messages."""
        import raven.embeddings as embeddings_module

        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1] * 384
        mock_model.encode.return_value = mock_embedding

        with patch.object(embeddings_module, "_get_model", return_value=mock_model):
            embeddings_module.generate_embedding("test text")

        captured = capsys.readouterr()
        assert "Loading sentence_transformers..." in captured.out
        assert "sentence_transformers loaded." in captured.out

    def test_generate_embeddings_batch_triggers_lazy_load(
        self, reset_module_state, capsys
    ):
        """generate_embeddings_batch triggers lazy loading messages."""
        import raven.embeddings as embeddings_module

        mock_model = MagicMock()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [[0.1] * 384]
        mock_model.encode.return_value = mock_embedding

        with patch.object(embeddings_module, "_get_model", return_value=mock_model):
            embeddings_module.generate_embeddings_batch(["test text"])

        captured = capsys.readouterr()
        assert "Loading sentence_transformers..." in captured.out
        assert "sentence_transformers loaded." in captured.out

    def test_clean_model_cache_resets_loaded_flag(self, reset_module_state):
        """clean_model_cache resets the _model_loaded flag."""
        import raven.embeddings as embeddings_module

        # First mark as loaded
        embeddings_module._model_loaded = True

        # Clean the cache (mock the cache dir)
        with patch.object(embeddings_module, "_get_model_cache_dir") as mock_cache_dir:
            mock_path = MagicMock()
            mock_path.exists.return_value = False
            mock_cache_dir.return_value = mock_path

            embeddings_module.clean_model_cache()

        # Should be reset to False
        assert embeddings_module._model_loaded is False


class TestLazyImportErrorHandling:
    """Tests for error handling in lazy import."""

    @pytest.fixture(autouse=True)
    def reset_module_state(self):
        """Reset module state before each test."""
        import raven.embeddings as embeddings_module

        original_model = embeddings_module._model
        original_loaded = embeddings_module._model_loaded

        embeddings_module._model = None
        embeddings_module._model_loaded = False

        yield

        embeddings_module._model = original_model
        embeddings_module._model_loaded = original_loaded

    def test_generate_embedding_empty_text_raises(self, reset_module_state):
        """generate_embedding raises ValueError for empty text."""
        import raven.embeddings as embeddings_module

        with pytest.raises(ValueError, match="Text cannot be empty"):
            embeddings_module.generate_embedding("")

    def test_generate_embedding_whitespace_only_raises(self, reset_module_state):
        """generate_embedding raises ValueError for whitespace-only text."""
        import raven.embeddings as embeddings_module

        with pytest.raises(ValueError, match="Text cannot be empty"):
            embeddings_module.generate_embedding("   ")

    def test_generate_embeddings_batch_empty_list_raises(self, reset_module_state):
        """generate_embeddings_batch raises ValueError for empty list."""
        import raven.embeddings as embeddings_module

        with pytest.raises(ValueError, match="Texts list cannot be empty"):
            embeddings_module.generate_embeddings_batch([])
