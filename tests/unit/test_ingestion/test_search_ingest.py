"""Unit tests for ingest_search_results function.

Run with: pytest tests/unit/test_ingestion/test_search_ingest.py -v
"""

from raven.ingestion import ingest_search_results
from raven.storage import init_database


class TestIngestSearchResults:
    """Tests for ingest_search_results function."""

    def test_ingest_search_results_success(self, tmp_path, mocker):
        """ingest_search_results batch processes papers."""
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.ingestion.pipeline.get_paper_id_by_identifier"
        )
        mock_get_embedding_exists = mocker.patch(
            "raven.ingestion.pipeline.get_embedding_exists"
        )
        mock_add_paper = mocker.patch("raven.ingestion.pipeline.add_paper")
        _mock_update_paper = mocker.patch("raven.ingestion.pipeline.update_paper")
        mock_generate_batch = mocker.patch(
            "raven.ingestion.pipeline.generate_embeddings_batch"
        )
        mock_add_embedding = mocker.patch("raven.ingestion.pipeline.add_embedding")

        mock_get_paper_id_by_identifier.return_value = None
        mock_get_embedding_exists.return_value = False
        mock_add_paper.side_effect = [1, 2, 3]
        mock_generate_batch.return_value = [
            [0.1] * 384,
            [0.2] * 384,
            [0.3] * 384,
        ]

        db_path = tmp_path / "test.db"
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

        db_path = tmp_path / "test.db"
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

    def test_ingest_search_results_empty(self, tmp_path, mocker):
        """ingest_search_results handles empty results."""
        mocker.patch("raven.storage._load_vector_extension")

        mock_get_paper_id_by_identifier = mocker.patch(
            "raven.ingestion.pipeline.get_paper_id_by_identifier"
        )
        _mock_get_embedding_exists = mocker.patch(
            "raven.ingestion.pipeline.get_embedding_exists"
        )
        mock_add_paper = mocker.patch("raven.ingestion.pipeline.add_paper")
        _mock_update_paper = mocker.patch("raven.ingestion.pipeline.update_paper")
        mock_generate_batch = mocker.patch(
            "raven.ingestion.pipeline.generate_embeddings_batch"
        )
        _mock_add_embedding = mocker.patch("raven.ingestion.pipeline.add_embedding")

        search_results = {"results": []}

        db_path = tmp_path / "test.db"
        results = ingest_search_results(db_path, search_results)

        assert results == []
        mock_get_paper_id_by_identifier.assert_not_called()
        mock_add_paper.assert_not_called()
        mock_generate_batch.assert_not_called()

    def test_ingest_search_results_skips_duplicates(self, tmp_path, mocker):
        """ingest_search_results handles duplicate identifiers (updates embedding if available)."""
        mocker.patch("raven.storage._load_vector_extension")

        _mock_add_paper = mocker.patch("raven.ingestion.pipeline.add_paper")
        mock_get_paper_id = mocker.patch(
            "raven.ingestion.pipeline.get_paper_id_by_identifier"
        )
        mock_get_embedding_exists = mocker.patch(
            "raven.ingestion.pipeline.get_embedding_exists"
        )
        mock_generate_batch = mocker.patch(
            "raven.ingestion.pipeline.generate_embeddings_batch"
        )
        mock_add_embedding = mocker.patch("raven.ingestion.pipeline.add_embedding")

        mock_get_paper_id.return_value = 1
        mock_get_embedding_exists.return_value = True
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

        db_path = tmp_path / "test.db"
        results = ingest_search_results(db_path, search_results)

        assert len(results) == 1
        assert results[0]["identifier"] == "doi:10.1234/duplicate"
        assert results[0]["paper_id"] == 1
        mock_add_embedding.assert_not_called()
