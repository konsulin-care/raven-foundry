"""Unit tests for raven.ingestion module.

Run with: pytest tests/test_ingestion.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from raven.ingestion import (
    combine_title_abstract,
    format_search_result,
    ingest_paper,
    ingest_search_results,
    normalize_doi,
    undo_inverted_index,
)


class TestNormalizeDoi:
    """Tests for normalize_doi function."""

    def test_normalize_doi_removes_https_prefix(self):
        """normalize_doi removes https://doi.org/ prefix."""
        assert normalize_doi("https://doi.org/10.1234/test") == "10.1234/test"

    def test_normalize_doi_removes_doi_prefix(self):
        """normalize_doi removes doi: prefix."""
        assert normalize_doi("doi:10.1234/test") == "10.1234/test"

    def test_normalize_doi_lowercases(self):
        """normalize_doi lowercases the DOI."""
        assert normalize_doi("10.1234/TEST") == "10.1234/test"

    def test_normalize_doi_strips_whitespace(self):
        """normalize_doi strips whitespace."""
        assert normalize_doi("  10.1234/test  ") == "10.1234/test"


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


class TestUndoInvertedIndex:
    """Tests for undo_inverted_index function."""

    def test_undo_inverted_index_simple(self):
        """Reconstructs text from inverted index."""
        inverted = {"hello": [0], "world": [1]}
        result = undo_inverted_index(inverted)
        assert result == "hello world"

    def test_undo_inverted_index_empty(self):
        """Returns empty string for empty inverted index."""
        result = undo_inverted_index({})
        assert result == ""

    def test_undo_inverted_index_none(self):
        """Returns empty string for None input."""
        result = undo_inverted_index(None)
        assert result == ""

    def test_undo_inverted_index_complex(self):
        """Handles complex inverted index with multiple positions."""
        inverted = {"the": [0, 3], "cat": [1], "sat": [2], "mat": [4]}
        result = undo_inverted_index(inverted)
        assert result == "the cat sat the mat"


class TestFormatSearchResult:
    """Tests for format_search_result function."""

    def test_format_search_result_basic(self):
        """Formats basic search result."""
        work = {
            "doi": "10.1234/test",
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2024,
            "cited_by_count": 10,
            "open_access": {"is_oa": True},
            "id": "https://openalex.org/W123",
            "relevance_score": 0.95,
        }
        result = format_search_result(work)

        assert result["doi"] == "10.1234/test"
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


class TestIngestPaper:
    """Tests for ingest_paper function."""

    @patch("raven.ingestion.add_embedding")
    @patch("raven.ingestion.generate_embedding")
    @patch("raven.ingestion.update_paper")
    @patch("raven.ingestion.add_paper")
    @patch("raven.ingestion.get_embedding_exists")
    @patch("raven.ingestion.get_paper_id_by_doi")
    @patch("raven.ingestion.get_openalex_api_key")
    @patch("raven.ingestion._create_session_with_retries")
    def test_ingest_paper_success(
        self,
        mock_session_cls,
        mock_api_key,
        mock_get_paper_id_by_doi,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_embedding,
        mock_add_embedding,
    ):
        """ingest_paper fetches paper, stores metadata and embedding."""
        # Setup mocks
        mock_api_key.return_value = "test-key"
        mock_get_paper_id_by_doi.return_value = None  # New DOI - doesn't exist
        mock_get_embedding_exists.return_value = False
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2024,
            "authorships": [{"author": {"display_name": "John Doe"}}],
            "host_venue": {"display_name": "Test Journal"},
            "id": "https://openalex.org/W123",
        }
        mock_session.get.return_value = mock_response

        mock_add_paper.return_value = 42
        mock_generate_embedding.return_value = [0.1] * 384

        # Execute
        db_path = Path("/tmp/test.db")
        result = ingest_paper(db_path, "10.1234/test")

        # Verify
        assert result is not None
        assert result["paper_id"] == 42
        assert result["doi"] == "10.1234/test"
        assert result["title"] == "Test Paper"
        assert result["type"] == "article"
        assert result["embedding"] == [0.1] * 384

        mock_get_paper_id_by_doi.assert_called_once_with(db_path, "10.1234/test")
        mock_add_paper.assert_called_once()
        mock_generate_embedding.assert_called_once_with("Test Paper")
        mock_add_embedding.assert_called_once_with(db_path, 42, [0.1] * 384)

    @patch("raven.ingestion.add_embedding")
    @patch("raven.ingestion.generate_embedding")
    @patch("raven.ingestion.update_paper")
    @patch("raven.ingestion.add_paper")
    @patch("raven.ingestion.get_embedding_exists")
    @patch("raven.ingestion.get_paper_id_by_doi")
    @patch("raven.ingestion.get_openalex_api_key")
    @patch("raven.ingestion._create_session_with_retries")
    def test_ingest_paper_api_error(
        self,
        mock_session_cls,
        mock_api_key,
        mock_get_paper_id_by_doi,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_embedding,
        mock_add_embedding,
    ):
        """ingest_paper returns None on API error."""
        mock_api_key.return_value = "test-key"
        mock_get_paper_id_by_doi.return_value = None
        mock_get_embedding_exists.return_value = False
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        db_path = Path("/tmp/test.db")
        result = ingest_paper(db_path, "10.1234/test")

        assert result is None

    @patch("raven.ingestion.add_embedding")
    @patch("raven.ingestion.generate_embedding")
    @patch("raven.ingestion.update_paper")
    @patch("raven.ingestion.add_paper")
    @patch("raven.ingestion.get_embedding_exists")
    @patch("raven.ingestion.get_paper_id_by_doi")
    @patch("raven.ingestion.get_openalex_api_key")
    @patch("raven.ingestion._create_session_with_retries")
    def test_ingest_paper_network_error(
        self,
        mock_session_cls,
        mock_api_key,
        mock_get_paper_id_by_doi,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_embedding,
        mock_add_embedding,
    ):
        """ingest_paper returns None on network error."""
        mock_api_key.return_value = "test-key"
        mock_get_paper_id_by_doi.return_value = None
        mock_get_embedding_exists.return_value = False
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.side_effect = requests.exceptions.RequestException(
            "Connection error"
        )

        db_path = Path("/tmp/test.db")
        result = ingest_paper(db_path, "10.1234/test")

        assert result is None


class TestIngestSearchResults:
    """Tests for ingest_search_results function."""

    @patch("raven.ingestion.add_embedding")
    @patch("raven.ingestion.generate_embeddings_batch")
    @patch("raven.ingestion.update_paper")
    @patch("raven.ingestion.add_paper")
    @patch("raven.ingestion.get_embedding_exists")
    @patch("raven.ingestion.get_paper_id_by_doi")
    def test_ingest_search_results_success(
        self,
        mock_get_paper_id_by_doi,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_batch,
        mock_add_embedding,
    ):
        """ingest_search_results batch processes papers."""
        mock_get_paper_id_by_doi.return_value = None  # All new DOIs
        mock_get_embedding_exists.return_value = False
        mock_add_paper.side_effect = [1, 2, 3]
        mock_generate_batch.return_value = [
            [0.1] * 384,
            [0.2] * 384,
            [0.3] * 384,
        ]

        search_results = {
            "results": [
                {
                    "doi": "10.1234/one",
                    "title": "Paper One",
                    "type": "article",
                    "publication_year": 2024,
                    "authorships": [],
                    "host_venue": {},
                    "id": "https://openalex.org/W1",
                },
                {
                    "doi": "10.1234/two",
                    "title": "Paper Two",
                    "type": "article",
                    "publication_year": 2023,
                    "authorships": [],
                    "host_venue": {},
                    "id": "https://openalex.org/W2",
                },
                {
                    "doi": "10.1234/three",
                    "title": "Paper Three",
                    "type": "article",
                    "publication_year": 2022,
                    "authorships": [],
                    "host_venue": {},
                    "id": "https://openalex.org/W3",
                },
            ]
        }

        db_path = Path("/tmp/test.db")
        results = ingest_search_results(db_path, search_results)

        assert len(results) == 3
        assert results[0]["paper_id"] == 1
        assert results[0]["doi"] == "10.1234/one"
        assert results[1]["paper_id"] == 2
        assert results[2]["paper_id"] == 3

        assert mock_get_paper_id_by_doi.call_count == 3
        mock_add_paper.assert_called()
        mock_generate_batch.assert_called_once()
        assert mock_add_embedding.call_count == 3

    @patch("raven.ingestion.add_embedding")
    @patch("raven.ingestion.generate_embeddings_batch")
    @patch("raven.ingestion.update_paper")
    @patch("raven.ingestion.add_paper")
    @patch("raven.ingestion.get_embedding_exists")
    @patch("raven.ingestion.get_paper_id_by_doi")
    def test_ingest_search_results_empty(
        self,
        mock_get_paper_id_by_doi,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_batch,
        mock_add_embedding,
    ):
        """ingest_search_results handles empty results."""
        search_results = {"results": []}

        db_path = Path("/tmp/test.db")
        results = ingest_search_results(db_path, search_results)

        assert results == []
        mock_get_paper_id_by_doi.assert_not_called()
        mock_add_paper.assert_not_called()
        mock_generate_batch.assert_not_called()

    @patch("raven.ingestion.add_embedding")
    @patch("raven.ingestion.generate_embeddings_batch")
    @patch("raven.ingestion.get_embedding_exists")
    @patch("raven.ingestion.get_paper_id_by_doi")
    @patch("raven.ingestion.add_paper")
    def test_ingest_search_results_skips_duplicates(
        self,
        mock_add_paper,
        mock_get_paper_id,
        mock_get_embedding_exists,
        mock_generate_batch,
        mock_add_embedding,
    ):
        """ingest_search_results handles duplicate DOIs (updates embedding if available)."""
        # Existing paper with embedding exists - should skip
        mock_get_paper_id.return_value = 1  # Existing paper ID
        mock_get_embedding_exists.return_value = True  # Embedding exists
        mock_generate_batch.return_value = [[0.1] * 384]

        search_results = {
            "results": [
                {
                    "doi": "10.1234/duplicate",
                    "title": "Duplicate Paper",
                    "type": "article",
                    "publication_year": 2024,
                    "authorships": [],
                    "host_venue": {},
                    "id": "https://openalex.org/W1",
                }
            ]
        }

        db_path = Path("/tmp/test.db")
        results = ingest_search_results(db_path, search_results)

        # With embedding available, should skip (not add embedding again)
        assert len(results) == 1
        assert results[0]["doi"] == "10.1234/duplicate"
        assert results[0]["paper_id"] == 1
        mock_add_embedding.assert_not_called()  # Should skip since embedding exists
