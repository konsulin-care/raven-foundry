"""Unit tests for ingestion helper functions.

Run with: pytest tests/unit/test_ingestion/test_helpers.py -v
"""

from raven.ingestion import (
    _get_existing_paper_info,
    _handle_existing_paper,
    prepare_paper_info,
)
from raven.storage import init_database


class TestGetExistingPaperInfo:
    """Tests for _get_existing_paper_info helper."""

    def test_returns_none_when_paper_not_exists(self, tmp_path, mocker):
        """Returns (None, False) when identifier doesn't exist."""
        mocker.patch("raven.ingestion.pipeline.get_paper_id_by_identifier")
        mocker.patch("raven.ingestion.pipeline.get_embedding_exists")
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.ingestion.pipeline.get_paper_id_by_identifier"
        )
        mock_get_paper_id_by_identifier.return_value = None

        db_path = tmp_path / "test.db"
        init_database(db_path)
        existing_id, has_embedding = _get_existing_paper_info(
            db_path, "doi:10.1234/new"
        )

        assert existing_id is None
        assert has_embedding is False
        mock_get_paper_id_by_identifier.assert_called_once_with(
            db_path, "doi:10.1234/new"
        )

    def test_returns_id_and_false_when_no_embedding(self, tmp_path, mocker):
        """Returns (id, False) when paper exists but no embedding."""
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.ingestion.pipeline.get_paper_id_by_identifier"
        )
        mock_get_embedding_exists = mocker.patch(
            "raven.ingestion.pipeline.get_embedding_exists"
        )
        mock_get_paper_id_by_identifier.return_value = 42
        mock_get_embedding_exists.return_value = False

        db_path = tmp_path / "test.db"
        init_database(db_path)
        existing_id, has_embedding = _get_existing_paper_info(
            db_path, "doi:10.1234/exists"
        )

        assert existing_id == 42
        assert has_embedding is False
        mock_get_embedding_exists.assert_called_once_with(db_path, 42)

    def test_returns_id_and_true_when_has_embedding(self, tmp_path, mocker):
        """Returns (id, True) when paper has embedding."""
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.ingestion.pipeline.get_paper_id_by_identifier"
        )
        mock_get_embedding_exists = mocker.patch(
            "raven.ingestion.pipeline.get_embedding_exists"
        )
        mock_get_paper_id_by_identifier.return_value = 42
        mock_get_embedding_exists.return_value = True

        db_path = tmp_path / "test.db"
        init_database(db_path)
        existing_id, has_embedding = _get_existing_paper_info(
            db_path, "doi:10.1234/embedded"
        )

        assert existing_id == 42
        assert has_embedding is True


class TestHandleExistingPaper:
    """Tests for _handle_existing_paper helper."""

    def test_returns_none_when_fully_stored(self, tmp_path, mocker):
        """Returns None when paper has embedding (already fully stored)."""
        mocker.patch("raven.storage._load_vector_extension")

        mock_update_paper = mocker.patch("raven.ingestion.pipeline.update_paper")
        mock_logger = mocker.patch("raven.ingestion.pipeline.logger")

        db_path = tmp_path / "test.db"
        init_database(db_path)
        paper_info = {"title": "Test Paper", "identifier": "doi:10.1234/test"}

        result = _handle_existing_paper(
            db_path, "doi:10.1234/test", paper_info, existing_id=1, has_embedding=True
        )

        assert result is None
        mock_update_paper.assert_not_called()
        mock_logger.info.assert_called_once()

    def test_updates_and_returns_id_when_no_embedding(self, tmp_path, mocker):
        """Updates paper and returns ID when no embedding."""
        mocker.patch("raven.storage._load_vector_extension")

        mock_update_paper = mocker.patch("raven.ingestion.pipeline.update_paper")
        _mock_logger = mocker.patch("raven.ingestion.pipeline.logger")

        db_path = tmp_path / "test.db"
        init_database(db_path)
        paper_info = {"title": "Test Paper", "identifier": "doi:10.1234/test"}

        result = _handle_existing_paper(
            db_path, "doi:10.1234/test", paper_info, existing_id=42, has_embedding=False
        )

        assert result == 42
        mock_update_paper.assert_called_once()
        call_kwargs = mock_update_paper.call_args[1]
        assert "identifier" not in call_kwargs


class TestPreparePaperInfo:
    """Tests for prepare_paper_info helper."""

    def test_extracts_basic_fields(self):
        """Extracts identifier, title, type from work."""
        work = {
            "ids": {"doi": "https://doi.org/10.1234/test"},
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2024,
            "authorships": [],
            "primary_location": {},
            "id": "https://openalex.org/W123",
        }

        paper_info, embedding_text = prepare_paper_info(work)

        assert paper_info["identifier"] == "doi:10.1234/test"
        assert paper_info["title"] == "Test Paper"
        assert paper_info["paper_type"] == "article"
        assert paper_info["year"] == 2024
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

        paper_info, _ = prepare_paper_info(work)

        assert paper_info["authors"] == "John Doe, Jane Smith"

    def test_extracts_venue(self):
        """Extracts venue from primary_location.source."""
        work = {
            "ids": {"doi": "https://doi.org/10.1234/test"},
            "title": "Test Paper",
            "primary_location": {"source": {"display_name": "Test Journal"}},
        }

        paper_info, _ = prepare_paper_info(work)

        assert paper_info["source"] == "Test Journal"

    def test_extracts_openalex_id_fallback(self):
        """Falls back to openalex ID when no DOI available."""
        work = {
            "ids": {"openalex": "https://openalex.org/W123456"},
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2024,
            "authorships": [],
            "primary_location": {},
            "id": "https://openalex.org/W123456",
        }

        paper_info, _ = prepare_paper_info(work)

        assert paper_info["identifier"] == "openalex:W123456"
        assert paper_info["title"] == "Test Paper"

    def test_handles_missing_fields(self):
        """Handles missing fields gracefully."""
        work = {"title": "Test Paper"}

        paper_info, embedding_text = prepare_paper_info(work)

        assert paper_info["identifier"] is None
        assert paper_info["title"] == "Test Paper"
        assert paper_info["authors"] is None
        assert paper_info["abstract"] == ""
        assert paper_info["source"] is None
        assert paper_info["paper_type"] == "article"
        assert embedding_text == "Test Paper"
