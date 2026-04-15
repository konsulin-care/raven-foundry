"""Unit tests for undo_inverted_index function.

Run with: pytest tests/unit/test_ingestion/test_abstract.py -v
"""

from raven.ingestion import undo_inverted_index


class TestUndoInvertedIndex:
    """Tests for undo_inverted_index function."""

    # Sample inverted index for testing
    SAMPLE_INVERTED_INDEX = {
        "Hello": [0],
        "world": [1],
        "this": [2, 5],
        "is": [3],
        "a": [4],
        "test": [6],
    }

    def test_undo_inverted_index_basic(self):
        """Reconstructs basic text from inverted index."""
        result = undo_inverted_index(self.SAMPLE_INVERTED_INDEX)

        # Note: "this" appears at positions [2, 5], so it appears twice
        assert result == "Hello world this is a this test"

    def test_undo_inverted_index_with_example_from_user(self):
        """Test with the example provided in the task."""
        # Use a smaller sample from the user's example
        sample_index = {
            "Despite": [0],
            "growing": [1],
            "interest": [2],
            "in": [3],
            "Open": [4],
            "Access": [5],
        }

        result = undo_inverted_index(sample_index)

        assert result == "Despite growing interest in Open Access"

    def test_undo_inverted_index_empty_dict(self):
        """Handles empty dictionary."""
        result = undo_inverted_index({})

        assert result == ""

    def test_undo_inverted_index_none_input(self):
        """Returns empty string for None input."""
        result = undo_inverted_index(None)

        assert result == ""

    def test_undo_inverted_index_preserves_word_order(self):
        """Correctly orders words by their positions."""
        # Same word at multiple positions
        multi_position_index = {
            "the": [0, 3, 6],
            "cat": [1],
            "sat": [2],
            "on": [4],
            "mat": [5],
        }

        result = undo_inverted_index(multi_position_index)

        # "the" appears at positions 0, 3, 6
        assert result == "the cat sat the on mat the"

    def test_undo_inverted_index_simple(self):
        """Reconstructs text from simple inverted index."""
        inverted = {"hello": [0], "world": [1]}
        result = undo_inverted_index(inverted)
        assert result == "hello world"

    def test_undo_inverted_index_complex(self):
        """Handles complex inverted index with multiple positions."""
        inverted = {"the": [0, 3], "cat": [1], "sat": [2], "mat": [4]}
        result = undo_inverted_index(inverted)
        assert result == "the cat sat the mat"
