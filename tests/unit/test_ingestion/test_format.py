"""Unit tests for format_search_result function.

Run with: pytest tests/unit/test_ingestion/test_format.py -v
"""

from raven.ingestion import format_search_result


class TestFormatSearchResult:
    """Tests for format_search_result function."""

    def test_format_search_result_basic(self):
        """Formats basic search result."""
        work = {
            "ids": {"doi": "https://doi.org/10.1234/test"},
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2024,
            "cited_by_count": 10,
            "open_access": {"is_oa": True},
            "id": "https://openalex.org/W123",
            "relevance_score": 0.95,
        }
        result = format_search_result(work)

        assert result["identifier"] == "doi:10.1234/test"
        assert result["title"] == "Test Paper"
        assert result["type"] == "article"
        assert result["publication_year"] == 2024
        assert result["cited_by_count"] == 10
        assert result["open_access"] is True
        assert result["embedding_text"] == "Test Paper"

    def test_format_search_result_with_abstract(self):
        """Includes abstract in embedding_text."""
        work = {
            "title": "Test Paper",
            "abstract_inverted_index": {"hello": [0], "world": [1]},
        }
        result = format_search_result(work)

        assert result["abstract"] == "hello world"
        assert result["embedding_text"] == "Test Paper hello world"

    def test_format_search_result_missing_fields(self):
        """Handles missing fields gracefully."""
        work = {}
        result = format_search_result(work)

        assert result["title"] == "Untitled"
        assert result["type"] == "article"
        assert result["abstract"] == ""
        assert result["embedding_text"] == "Untitled"
        assert result["identifier"] is None

    def test_format_search_result_with_abstract_from_test_unit(self):
        """format_search_result includes reconstructed abstract."""
        work = {
            "ids": {"doi": "10.1234/test"},
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2023,
            "cited_by_count": 50,
            "open_access": {"is_oa": True},
            "abstract_inverted_index": {
                "This": [0],
                "is": [1],
                "abstract": [2],
            },
        }

        result = format_search_result(work)

        assert result["abstract"] == "This is abstract"
        assert result["identifier"] == "doi:10.1234/test"
        assert result["publication_year"] == 2023
        assert result["type"] == "article"
        assert result["cited_by_count"] == 50
        assert result["open_access"] is True

    def test_format_search_result_without_abstract(self):
        """format_search_result handles missing abstract_inverted_index."""
        work = {
            "ids": {"doi": "10.1234/test"},
            "title": "Test Paper Without Abstract",
            "type": "preprint",
            "publication_year": 2022,
        }

        result = format_search_result(work)

        assert result["abstract"] == ""
        assert result["embedding_text"] == "Test Paper Without Abstract"
        assert result["identifier"] == "doi:10.1234/test"
