"""Unit tests for combine_title_abstract function.

Run with: pytest tests/unit/test_ingestion/test_combine.py -v
"""

from raven.ingestion import combine_title_abstract


class TestCombineTitleAbstract:
    """Tests for combine_title_abstract function."""

    def test_combine_with_abstract(self):
        """combine_title_abstract returns title + abstract when abstract exists."""
        result = combine_title_abstract("Test Title", "This is the abstract.")
        assert result == "Test Title This is the abstract."

    def test_combine_with_empty_abstract(self):
        """combine_title_abstract returns title only when abstract is empty."""
        result = combine_title_abstract("Test Title", "")
        assert result == "Test Title"

    def test_combine_with_none_abstract(self):
        """combine_title_abstract returns title only when abstract is None."""
        result = combine_title_abstract("Test Title", None)
        assert result == "Test Title"

    def test_combine_with_whitespace_abstract(self):
        """combine_title_abstract returns title only when abstract is whitespace."""
        result = combine_title_abstract("Test Title", "   ")
        assert result == "Test Title"
