"""Unit tests for raven.ingestion module.

Run with: pytest tests/test_ingestion.py -v
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from raven.ingestion import (
    _get_existing_paper_info,
    _handle_existing_paper,
    _prepare_paper_info,
    combine_title_abstract,
    format_search_result,
    ingest_paper,
    ingest_search_results,
    normalize_doi,
    undo_inverted_index,
)
from raven.storage import init_database


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


class TestNormalizeIdentifier:
    """Tests for normalize_identifier function."""

    def test_doi_with_explicit_prefix(self):
        """normalize_identifier handles explicit doi: prefix."""
        from raven.ingestion import normalize_identifier

        assert normalize_identifier("doi:10.1234/test") == "doi:10.1234/test"

    def test_doi_without_prefix(self):
        """normalize_identifier adds doi: prefix to bare DOI."""
        from raven.ingestion import normalize_identifier

        assert normalize_identifier("10.1234/test") == "doi:10.1234/test"

    def test_doi_url(self):
        """normalize_identifier handles DOI URL."""
        from raven.ingestion import normalize_identifier

        assert (
            normalize_identifier("https://doi.org/10.1234/test") == "doi:10.1234/test"
        )

    def test_openalex_with_explicit_prefix(self):
        """normalize_identifier handles explicit openalex: prefix."""
        from raven.ingestion import normalize_identifier

        assert normalize_identifier("openalex:W7119934875") == "openalex:w7119934875"

    def test_openalex_bare_id(self):
        """normalize_identifier handles bare OpenAlex ID."""
        from raven.ingestion import normalize_identifier

        assert normalize_identifier("W7119934875") == "openalex:W7119934875"

    def test_openalex_url(self):
        """normalize_identifier handles OpenAlex URL."""
        from raven.ingestion import normalize_identifier

        assert (
            normalize_identifier("https://openalex.org/W7119934875")
            == "openalex:w7119934875"
        )

    def test_pmid_with_explicit_prefix(self):
        """normalize_identifier handles explicit pmid: prefix."""
        from raven.ingestion import normalize_identifier

        assert normalize_identifier("pmid:29456894") == "pmid:29456894"

    def test_pmid_bare_id(self):
        """normalize_identifier treats 7+ digits as PMID."""
        from raven.ingestion import normalize_identifier

        assert normalize_identifier("29456894") == "pmid:29456894"

    def test_pmid_url(self):
        """normalize_identifier handles PubMed URL."""
        from raven.ingestion import normalize_identifier

        assert (
            normalize_identifier("https://pubmed.ncbi.nlm.nih.gov/29456894")
            == "pmid:29456894"
        )

    def test_mag_with_prefix(self):
        """normalize_identifier handles explicit mag: prefix."""
        from raven.ingestion import normalize_identifier

        assert normalize_identifier("mag:2741809807") == "mag:2741809807"

    def test_short_digits_as_mag(self):
        """normalize_identifier treats short digits (1-6) as MAG."""
        from raven.ingestion import normalize_identifier

        # 6 digits or less is treated as MAG (less common for PMID)
        assert normalize_identifier("123456") == "mag:123456"


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


class TestIngestPaper:
    """Tests for ingest_paper function."""

    @patch("raven.ingestion.pipeline.add_embedding")
    @patch("raven.ingestion.pipeline.generate_embedding")
    @patch("raven.ingestion.pipeline.update_paper")
    @patch("raven.ingestion.pipeline.add_paper")
    @patch("raven.ingestion.pipeline.get_embedding_exists")
    @patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
    @patch("raven.ingestion.get_openalex_api_key")
    @patch("raven.ingestion.api._create_session_with_retries")
    def test_ingest_paper_success(
        self,
        mock_session_cls,
        mock_api_key,
        mock_get_paper_id_by_identifier,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_embedding,
        mock_add_embedding,
    ):
        """ingest_paper fetches paper, stores metadata and embedding."""
        # Setup mocks
        mock_api_key.return_value = "test-key"
        mock_get_paper_id_by_identifier.return_value = (
            None  # New identifier - doesn't exist
        )
        mock_get_embedding_exists.return_value = False
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "ids": {"doi": "https://doi.org/10.1234/test"},
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
        assert result["identifier"] == "doi:10.1234/test"
        assert result["title"] == "Test Paper"
        assert result["type"] == "article"
        assert result["embedding"] == [0.1] * 384

        mock_get_paper_id_by_identifier.assert_called_once_with(
            db_path, "doi:10.1234/test"
        )
        mock_add_paper.assert_called_once()
        mock_generate_embedding.assert_called_once_with("Test Paper")
        mock_add_embedding.assert_called_once_with(db_path, 42, [0.1] * 384)

    @patch("raven.storage.add_embedding")
    @patch("raven.ingestion.pipeline.generate_embedding")
    @patch("raven.storage.update_paper")
    @patch("raven.storage.add_paper")
    @patch("raven.storage.get_embedding_exists")
    @patch("raven.storage.get_paper_id_by_identifier")
    @patch("raven.ingestion.get_openalex_api_key")
    @patch("raven.ingestion.api._create_session_with_retries")
    def test_ingest_paper_api_error(
        self,
        mock_session_cls,
        mock_api_key,
        mock_get_paper_id_by_identifier,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_embedding,
        mock_add_embedding,
    ):
        """ingest_paper returns None on API error."""
        mock_api_key.return_value = "test-key"
        mock_get_paper_id_by_identifier.return_value = None
        mock_get_embedding_exists.return_value = False
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        db_path = Path("/tmp/test.db")
        result = ingest_paper(db_path, "10.1234/test")

        assert result is None

    @patch("raven.storage.add_embedding")
    @patch("raven.ingestion.pipeline.generate_embedding")
    @patch("raven.storage.update_paper")
    @patch("raven.storage.add_paper")
    @patch("raven.storage.get_embedding_exists")
    @patch("raven.storage.get_paper_id_by_identifier")
    @patch("raven.ingestion.get_openalex_api_key")
    @patch("raven.ingestion.api._create_session_with_retries")
    def test_ingest_paper_network_error(
        self,
        mock_session_cls,
        mock_api_key,
        mock_get_paper_id_by_identifier,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_embedding,
        mock_add_embedding,
    ):
        """ingest_paper returns None on network error."""
        mock_api_key.return_value = "test-key"
        mock_get_paper_id_by_identifier.return_value = None
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

    @patch("raven.ingestion.pipeline.add_embedding")
    @patch("raven.ingestion.pipeline.generate_embeddings_batch")
    @patch("raven.ingestion.pipeline.update_paper")
    @patch("raven.ingestion.pipeline.add_paper")
    @patch("raven.ingestion.pipeline.get_embedding_exists")
    @patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
    def test_ingest_search_results_success(
        self,
        mock_get_paper_id_by_identifier,
        mock_get_embedding_exists,
        mock_add_paper,
        mock_update_paper,
        mock_generate_batch,
        mock_add_embedding,
    ):
        """ingest_search_results batch processes papers."""
        mock_get_paper_id_by_identifier.return_value = None  # All new identifiers
        mock_get_embedding_exists.return_value = False
        mock_add_paper.side_effect = [1, 2, 3]
        mock_generate_batch.return_value = [
            [0.1] * 384,
            [0.2] * 384,
            [0.3] * 384,
        ]

        db_path = Path("/tmp/test.db")
        init_database(db_path)

        search_results = {
            "results": [
                {
                    "ids": {"doi": "https://doi.org/10.1234/one"},
                    "title": "Paper One",
                    "type": "article",
                    "publication_year": 2024,
                    "authorships": [],
                    "host_venue": {},
                    "id": "https://openalex.org/W1",
                },
                {
                    "ids": {"doi": "https://doi.org/10.1234/two"},
                    "title": "Paper Two",
                    "type": "article",
                    "publication_year": 2023,
                    "authorships": [],
                    "host_venue": {},
                    "id": "https://openalex.org/W2",
                },
                {
                    "ids": {"doi": "https://doi.org/10.1234/three"},
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
        assert results[0]["identifier"] == "doi:10.1234/one"
        assert results[1]["paper_id"] == 2
        assert results[2]["paper_id"] == 3

        assert mock_get_paper_id_by_identifier.call_count == 3
        mock_add_paper.assert_called()
        mock_generate_batch.assert_called_once()
        assert mock_add_embedding.call_count == 3

    @patch("raven.ingestion.pipeline.add_embedding")
    @patch("raven.ingestion.pipeline.generate_embeddings_batch")
    @patch("raven.ingestion.pipeline.update_paper")
    @patch("raven.ingestion.pipeline.add_paper")
    @patch("raven.ingestion.pipeline.get_embedding_exists")
    @patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
    def test_ingest_search_results_empty(
        self,
        mock_get_paper_id_by_identifier,
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
        mock_get_paper_id_by_identifier.assert_not_called()
        mock_add_paper.assert_not_called()
        mock_generate_batch.assert_not_called()

    @patch("raven.ingestion.pipeline.add_embedding")
    @patch("raven.ingestion.pipeline.generate_embeddings_batch")
    @patch("raven.ingestion.pipeline.get_embedding_exists")
    @patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
    @patch("raven.ingestion.pipeline.add_paper")
    def test_ingest_search_results_skips_duplicates(
        self,
        mock_add_paper,
        mock_get_paper_id,
        mock_get_embedding_exists,
        mock_generate_batch,
        mock_add_embedding,
    ):
        """ingest_search_results handles duplicate identifiers (updates embedding if available)."""
        # Existing paper with embedding exists - should skip
        mock_get_paper_id.return_value = 1  # Existing paper ID
        mock_get_embedding_exists.return_value = True  # Embedding exists
        mock_generate_batch.return_value = [[0.1] * 384]

        search_results = {
            "results": [
                {
                    "ids": {"doi": "https://doi.org/10.1234/duplicate"},
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
        assert results[0]["identifier"] == "doi:10.1234/duplicate"
        assert results[0]["paper_id"] == 1
        mock_add_embedding.assert_not_called()  # Should skip since embedding exists


class TestGetExistingPaperInfo:
    """Tests for _get_existing_paper_info helper."""

    @patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
    @patch("raven.ingestion.pipeline.get_embedding_exists")
    def test_returns_none_when_paper_not_exists(
        self, mock_get_embedding_exists, mock_get_paper_id_by_identifier
    ):
        """Returns (None, False) when identifier doesn't exist."""
        mock_get_paper_id_by_identifier.return_value = None

        db_path = Path("/tmp/test.db")
        init_database(db_path)  # Initialize database
        existing_id, has_embedding = _get_existing_paper_info(
            db_path, "doi:10.1234/new"
        )

        assert existing_id is None
        assert has_embedding is False
        mock_get_paper_id_by_identifier.assert_called_once_with(
            db_path, "doi:10.1234/new"
        )
        mock_get_embedding_exists.assert_not_called()

    @patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
    @patch("raven.ingestion.pipeline.get_embedding_exists")
    def test_returns_id_and_false_when_no_embedding(
        self, mock_get_embedding_exists, mock_get_paper_id_by_identifier
    ):
        """Returns (id, False) when paper exists but no embedding."""
        mock_get_paper_id_by_identifier.return_value = 42
        mock_get_embedding_exists.return_value = False

        db_path = Path("/tmp/test.db")
        init_database(db_path)  # Initialize database
        existing_id, has_embedding = _get_existing_paper_info(
            db_path, "doi:10.1234/exists"
        )

        assert existing_id == 42
        assert has_embedding is False
        mock_get_embedding_exists.assert_called_once_with(db_path, 42)

    @patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
    @patch("raven.ingestion.pipeline.get_embedding_exists")
    def test_returns_id_and_true_when_has_embedding(
        self, mock_get_embedding_exists, mock_get_paper_id_by_identifier
    ):
        """Returns (id, True) when paper has embedding."""
        mock_get_paper_id_by_identifier.return_value = 42
        mock_get_embedding_exists.return_value = True

        db_path = Path("/tmp/test.db")
        init_database(db_path)  # Initialize database
        existing_id, has_embedding = _get_existing_paper_info(
            db_path, "doi:10.1234/embedded"
        )

        assert existing_id == 42
        assert has_embedding is True


class TestHandleExistingPaper:
    """Tests for _handle_existing_paper helper."""

    @patch("raven.ingestion.pipeline.update_paper")
    @patch("raven.ingestion.pipeline.logger")
    def test_returns_none_when_fully_stored(self, mock_logger, mock_update_paper):
        """Returns None when paper has embedding (already fully stored)."""
        db_path = Path("/tmp/test.db")
        init_database(db_path)  # Initialize database
        paper_info = {"title": "Test Paper", "identifier": "doi:10.1234/test"}

        result = _handle_existing_paper(
            db_path, "doi:10.1234/test", paper_info, existing_id=1, has_embedding=True
        )

        assert result is None
        mock_update_paper.assert_not_called()
        mock_logger.info.assert_called_once()

    @patch("raven.ingestion.pipeline.update_paper")
    @patch("raven.ingestion.pipeline.logger")
    def test_updates_and_returns_id_when_no_embedding(
        self, mock_logger, mock_update_paper
    ):
        """Updates paper and returns ID when no embedding."""
        db_path = Path("/tmp/test.db")
        init_database(db_path)  # Initialize database
        paper_info = {"title": "Test Paper", "identifier": "doi:10.1234/test"}

        result = _handle_existing_paper(
            db_path, "doi:10.1234/test", paper_info, existing_id=42, has_embedding=False
        )

        assert result == 42
        mock_update_paper.assert_called_once()
        # Check identifier was removed from paper_info
        call_kwargs = mock_update_paper.call_args[1]
        assert "identifier" not in call_kwargs


class TestPreparePaperInfo:
    """Tests for _prepare_paper_info helper."""

    def test_extracts_basic_fields(self):
        """Extracts identifier, title, type from work."""
        work = {
            "ids": {"doi": "https://doi.org/10.1234/test"},
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2024,
            "authorships": [],
            "host_venue": {},
            "id": "https://openalex.org/W123",
        }

        paper_info, embedding_text = _prepare_paper_info(work)

        assert paper_info["identifier"] == "doi:10.1234/test"
        assert paper_info["title"] == "Test Paper"
        assert paper_info["paper_type"] == "article"
        assert paper_info["publication_year"] == 2024
        assert paper_info["openalex_id"] == "https://openalex.org/W123"
        assert embedding_text == "Test Paper"

    def test_extracts_authors(self):
        """Extracts authors from authorship data."""
        work = {
            "ids": {"doi": "https://doi.org/10.1234/test"},
            "title": "Test Paper",
            "authorships": [
                {"author": {"display_name": "John Doe"}},
                {"author": {"display_name": "Jane Smith"}},
            ],
        }

        paper_info, _ = _prepare_paper_info(work)

        assert paper_info["authors"] == "John Doe, Jane Smith"

    def test_extracts_venue(self):
        """Extracts venue from host_venue."""
        work = {
            "ids": {"doi": "https://doi.org/10.1234/test"},
            "title": "Test Paper",
            "host_venue": {"display_name": "Test Journal"},
        }

        paper_info, _ = _prepare_paper_info(work)

        assert paper_info["venue"] == "Test Journal"

    def test_extracts_openalex_id_fallback(self):
        """Falls back to openalex ID when no DOI available."""
        work = {
            "ids": {"openalex": "https://openalex.org/W123456"},
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2024,
            "authorships": [],
            "host_venue": {},
            "id": "https://openalex.org/W123456",
        }

        paper_info, embedding_text = _prepare_paper_info(work)

        assert paper_info["identifier"] == "openalex:W123456"
        assert paper_info["title"] == "Test Paper"

    def test_handles_missing_fields(self):
        """Handles missing fields gracefully."""
        work = {"title": "Test Paper"}

        paper_info, embedding_text = _prepare_paper_info(work)

        assert paper_info["identifier"] is None
        assert paper_info["title"] == "Test Paper"
        assert paper_info["authors"] is None
        assert paper_info["abstract"] == ""
        assert paper_info["venue"] is None
        assert paper_info["paper_type"] == "article"
        assert embedding_text == "Test Paper"


class TestBibtexParsing:
    """Tests for BibTeX parsing module."""

    def test_extract_identifier_from_bibtex_doi(self):
        """extract_identifier_from_bibtex extracts DOI correctly."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"doi": "10.1234/test", "title": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "doi:10.1234/test"

    def test_extract_identifier_from_bibtex_doi_with_url(self):
        """extract_identifier_from_bibtex handles DOI with URL prefix."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"doi": "https://doi.org/10.1234/test", "title": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "doi:10.1234/test"

    def test_extract_identifier_from_bibtex_pmid(self):
        """extract_identifier_from_bibtex extracts PMID correctly."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"pmid": "29456894", "title": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "pmid:29456894"

    def test_extract_identifier_from_bibtex_pmcid(self):
        """extract_identifier_from_bibtex extracts PMCID correctly."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"pmcid": "PMC1234567", "title": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "pmcid:PMC1234567"

    def test_extract_identifier_from_bibtex_pmcid_without_prefix(self):
        """extract_identifier_from_bibtex adds PMC prefix if missing."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"pmcid": "1234567", "title": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "pmcid:PMC1234567"

    def test_extract_identifier_from_bibtex_mag(self):
        """extract_identifier_from_bibtex extracts MAG correctly."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"mag": "2741809807", "title": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "mag:2741809807"

    def test_extract_identifier_from_bibtex_openalex(self):
        """extract_identifier_from_bibtex extracts OpenAlex ID correctly."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"openalex": "W7119934875", "title": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "openalex:W7119934875"

    def test_extract_identifier_from_bibtex_priority_doi(self):
        """extract_identifier_from_bibtex prefers DOI over other IDs."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {
            "doi": "10.1234/test",
            "pmid": "29456894",
            "pmcid": "PMC1234567",
            "title": "Test Paper",
        }
        # DOI should be extracted first (highest priority)
        result = extract_identifier_from_bibtex(entry)
        assert result is not None
        assert result.startswith("doi:")

    def test_extract_identifier_from_bibtex_no_identifier(self):
        """extract_identifier_from_bibtex returns None for entries without identifiers."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"title": "Test Paper", "author": "John Doe"}
        assert extract_identifier_from_bibtex(entry) is None

    def test_extract_identifier_from_bibtex_case_insensitive(self):
        """extract_identifier_from_bibtex handles case-insensitive field names."""
        from raven.ingestion.bibtex import extract_identifier_from_bibtex

        entry = {"DOI": "10.1234/test", "TITLE": "Test Paper"}
        assert extract_identifier_from_bibtex(entry) == "doi:10.1234/test"


class TestFilterValidEntries:
    """Tests for filter_valid_entries function."""

    def test_filter_valid_entries_all_valid(self):
        """filter_valid_entries returns all entries as valid when they have identifiers."""
        from raven.ingestion.bibtex import filter_valid_entries

        entries = [
            {"doi": "10.1234/test1", "title": "Paper 1"},
            {"pmid": "29456894", "title": "Paper 2"},
            {"pmcid": "PMC1234567", "title": "Paper 3"},
        ]
        valid, invalid = filter_valid_entries(entries)

        assert len(valid) == 3
        assert len(invalid) == 0

    def test_filter_valid_entries_some_invalid(self):
        """filter_valid_entries correctly separates valid and invalid entries."""
        from raven.ingestion.bibtex import filter_valid_entries

        entries = [
            {"doi": "10.1234/test1", "title": "Paper 1"},
            {"title": "Paper 2"},  # No identifier
            {"pmid": "29456894", "title": "Paper 3"},
        ]
        valid, invalid = filter_valid_entries(entries)

        assert len(valid) == 2
        assert len(invalid) == 1

    def test_filter_valid_entries_adds_identifier(self):
        """filter_valid_entries adds _identifier to valid entries."""
        from raven.ingestion.bibtex import filter_valid_entries

        entries = [{"doi": "10.1234/test", "title": "Paper 1"}]
        valid, invalid = filter_valid_entries(entries)

        assert valid[0].get("_identifier") == "doi:10.1234/test"

    def test_filter_valid_entries_empty_list(self):
        """filter_valid_entries handles empty list."""
        from raven.ingestion.bibtex import filter_valid_entries

        valid, invalid = filter_valid_entries([])

        assert len(valid) == 0
        assert len(invalid) == 0
