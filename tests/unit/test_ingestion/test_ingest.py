"""Unit tests for ingest_paper function.

Run with: pytest tests/unit/test_ingestion/test_ingest.py -v
"""

from unittest.mock import MagicMock

import requests

from raven.ingestion import ingest_paper
from raven.storage import init_database


class TestIngestPaper:
    """Tests for ingest_paper function."""

    def test_ingest_paper_success(self, tmp_path, mocker, monkeypatch):
        """ingest_paper fetches paper, stores metadata and embedding."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.ingestion.pipeline.get_paper_id_by_identifier"
        )
        mock_get_embedding_exists = mocker.patch(
            "raven.ingestion.pipeline.get_embedding_exists"
        )
        mock_add_paper = mocker.patch("raven.ingestion.pipeline.add_paper")
        _mock_update_paper = mocker.patch("raven.ingestion.pipeline.update_paper")
        mock_generate_embedding = mocker.patch(
            "raven.ingestion.pipeline.generate_embedding"
        )
        mock_add_embedding = mocker.patch("raven.ingestion.pipeline.add_embedding")
        mock_session_cls = mocker.patch(
            "raven.ingestion.api._create_session_with_retries"
        )

        mock_get_paper_id_by_identifier.return_value = None
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

        db_path = tmp_path / "test.db"
        result = ingest_paper(db_path, "10.1234/test")

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
        mock_add_embedding.assert_called_once()
        call_args = mock_add_embedding.call_args
        assert call_args[0][0] == db_path
        assert call_args[0][1] == 42
        assert call_args[0][2] == [0.1] * 384
        assert call_args[0][3] == "Test Paper"
        assert call_args[1]["content_type"] == "title"

    def test_ingest_paper_api_error(self, tmp_path, mocker, monkeypatch):
        """ingest_paper returns None on API error."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.storage.get_paper_id_by_identifier"
        )
        mock_get_embedding_exists = mocker.patch("raven.storage.get_embedding_exists")
        _mock_add_paper = mocker.patch("raven.storage.add_paper")
        _mock_update_paper = mocker.patch("raven.storage.update_paper")
        _mock_generate_embedding = mocker.patch(
            "raven.ingestion.pipeline.generate_embedding"
        )
        _mock_add_embedding = mocker.patch("raven.storage.add_embedding")
        mock_session_cls = mocker.patch(
            "raven.ingestion.api._create_session_with_retries"
        )

        mock_get_paper_id_by_identifier.return_value = None
        mock_get_embedding_exists.return_value = False
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_session.get.return_value = mock_response

        db_path = tmp_path / "test.db"
        result = ingest_paper(db_path, "10.1234/test")

        assert result is None

    def test_ingest_paper_network_error(self, tmp_path, mocker, monkeypatch):
        """ingest_paper returns None on network error."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.storage.get_paper_id_by_identifier"
        )
        mock_get_embedding_exists = mocker.patch("raven.storage.get_embedding_exists")
        _mock_add_paper = mocker.patch("raven.storage.add_paper")
        _mock_update_paper = mocker.patch("raven.storage.update_paper")
        _mock_generate_embedding = mocker.patch(
            "raven.ingestion.pipeline.generate_embedding"
        )
        _mock_add_embedding = mocker.patch("raven.storage.add_embedding")
        mock_session_cls = mocker.patch(
            "raven.ingestion.api._create_session_with_retries"
        )

        mock_get_paper_id_by_identifier.return_value = None
        mock_get_embedding_exists.return_value = False
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.side_effect = requests.exceptions.RequestException(
            "Connection error"
        )

        db_path = tmp_path / "test.db"
        result = ingest_paper(db_path, "10.1234/test")

        assert result is None


class TestIngestionModule:
    """Tests for raven.ingestion module.

    These tests use monkeypatch to set environment variables,
    which is more robust than patching functions because it
    works regardless of where functions are imported.
    """

    def test_ingest_paper_success(self, tmp_path, requests_mock, monkeypatch):
        """Test successful paper ingestion."""
        mock_response = {
            "title": "Sample Research Paper",
            "type": "article",
        }

        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.get(
            "https://api.openalex.org/works/doi%3A10.1234%2Fsample",
            json=mock_response,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "10.1234/sample")

        assert result is not None
        assert result["title"] == "Sample Research Paper"
        assert result["type"] == "article"

    def test_ingest_paper_not_found(self, tmp_path, requests_mock, monkeypatch):
        """Test ingestion returns None when paper not found."""
        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.get(
            "https://api.openalex.org/works/doi%3A10.9999%2Fmissing",
            status_code=404,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "10.9999/missing")

        assert result is None

    def test_doi_cleaning_https_doi_org(self, tmp_path, requests_mock, monkeypatch):
        """Test DOI cleaning removes https://doi.org/ prefix."""
        mock_response = {"title": "Test", "type": "article"}

        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.register_uri(
            "GET",
            "https://api.openalex.org/works/doi%3A10.1234%2Ftest",
            json=mock_response,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "https://doi.org/10.1234/test")

        assert result is not None

    def test_doi_cleaning_doi_prefix(self, tmp_path, requests_mock, monkeypatch):
        """Test DOI cleaning removes doi: prefix."""
        mock_response = {
            "title": "Test",
            "type": "article",
            "ids": {"doi": "https://doi.org/10.1234/prefix"},
        }

        db_path = tmp_path / "test.db"
        init_database(db_path)

        requests_mock.register_uri(
            "GET",
            "https://api.openalex.org/works/doi%3A10.1234%2Fprefix",
            json=mock_response,
        )

        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        result = ingest_paper(db_path, "doi:10.1234/prefix")

        assert result is not None
        assert result["identifier"] == "doi:10.1234/prefix"
