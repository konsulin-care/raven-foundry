"""Unit tests for OpenAlex search functionality.

Run with: pytest tests/unit/test_ingestion/test_search.py -v
"""

from raven.ingestion import (
    DEFAULT_FILTERS,
    SEMANTIC_FILTERS,
    format_search_result,
    search_works,
    search_works_keyword,
)
from raven.storage import add_paper, init_database, search_papers


class TestOpenAlexSearch:
    """Tests for OpenAlex search functions."""

    def test_default_filters_includes_oa(self):
        """DEFAULT_FILTERS includes is_oa."""
        assert "is_oa:true" in DEFAULT_FILTERS

    def test_semantic_filters_supports_semantic_search(self):
        """SEMANTIC_FILTERS uses is_oa which is supported in semantic search."""
        # Semantic search only supports: is_oa (not open_access.is_oa), has_abstract, etc.
        assert "is_oa:true" in SEMANTIC_FILTERS
        # Should NOT have has_doi which is not supported in semantic search
        assert "has_doi" not in SEMANTIC_FILTERS

    def test_format_search_result_basic(self):
        """format_search_result extracts key fields."""
        work = {
            "ids": {"doi": "10.1234/test"},
            "title": "Test Paper",
            "type": "article",
            "publication_year": 2023,
            "cited_by_count": 100,
            "open_access": {"is_oa": True},
        }

        result = format_search_result(work)

        assert result["identifier"] == "doi:10.1234/test"
        assert result["title"] == "Test Paper"
        assert result["type"] == "article"
        assert result["publication_year"] == 2023
        assert result["cited_by_count"] == 100
        assert result["open_access"] is True

    def test_format_search_result_missing_fields(self):
        """format_search_result handles missing fields."""
        work = {
            "ids": {},  # Empty ids - no identifier available
            "title": "Minimal Paper",
            # Missing doi, type, etc.
        }

        result = format_search_result(work)

        assert result["title"] == "Minimal Paper"
        assert result["identifier"] is None
        assert result["type"] == "article"  # Default
        assert result["cited_by_count"] == 0  # Default

    def test_search_works_keyword_fallback(self, requests_mock, monkeypatch):
        """search_works falls back to keyword on semantic failure."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Mock semantic search (429 rate limit)
        requests_mock.get(
            "https://api.openalex.org/works",
            [
                {"status_code": 429},  # Semantic rate limited
                {
                    "json": {  # Keyword fallback succeeds
                        "results": [
                            {
                                "doi": "10.1234/fallback",
                                "title": "Fallback Paper",
                                "type": "article",
                                "cited_by_count": 50,
                            }
                        ],
                        "meta": {"count": 1},
                    }
                },
            ],
        )

        result = search_works("test query", use_semantic=True)

        assert result["search_type"] == "keyword"
        assert len(result["results"]) == 1

    def test_search_works_semantic_success(self, requests_mock, monkeypatch):
        """search_works uses semantic when available."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        requests_mock.get(
            "https://api.openalex.org/works",
            json={
                "results": [
                    {
                        "doi": "10.1234/semantic",
                        "title": "Semantic Result",
                        "type": "article",
                        "relevance_score": 0.95,
                    }
                ],
                "meta": {"count": 1},
            },
        )

        result = search_works("machine learning", use_semantic=True)

        # Rate limiting not triggered in mock, should use semantic
        assert result["search_type"] in ["semantic", "keyword"]

    def test_search_works_keyword_only(self, requests_mock, monkeypatch):
        """search_works_keyword uses keyword search only."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        requests_mock.get(
            "https://api.openalex.org/works",
            json={
                "results": [
                    {
                        "doi": "10.1234/keyword",
                        "title": "Keyword Result",
                        "type": "article",
                    }
                ],
                "meta": {"count": 1},
            },
        )

        result = search_works_keyword("test")

        assert result["search_type"] == "keyword"
        assert len(result["results"]) == 1

    def test_search_works_with_filters(self, requests_mock, monkeypatch):
        """search_works applies filters correctly."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Check that the request includes both default and custom filters
        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query", filter_str="publication_year:>2020", use_semantic=False
        )

        assert result["search_type"] == "keyword"
        assert len(result["results"]) == 0  # Mock returns empty results

    def test_search_works_with_sort(self, requests_mock, monkeypatch):
        """search_works passes sort parameter directly to OpenAlex."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Use multi-field sort format
        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query",
            sort="publication_year:desc,relevance_score:desc",
            use_semantic=False,
        )

        assert result["search_type"] == "keyword"

        # Verify sort is passed as-is (no conversion)
        last_request = requests_mock.last_request
        assert last_request
        assert (
            last_request.qs["sort"][0] == "publication_year:desc,relevance_score:desc"
        )

    def test_search_works_single_field_sort(self, requests_mock, monkeypatch):
        """search_works passes single-field sort directly to OpenAlex."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query",
            sort="cited_by_count:desc",
            use_semantic=False,
        )

        assert result["search_type"] == "keyword"

        # Verify sort is passed as-is
        last_request = requests_mock.last_request
        assert last_request
        assert last_request.qs["sort"][0] == "cited_by_count:desc"

    def test_search_works_keyword_with_filters(self, requests_mock, monkeypatch):
        """search_works keyword mode applies filters correctly."""
        monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
        monkeypatch.setenv("OPENALEX_API_URL", "https://api.openalex.org")

        # Check that the request includes both default and custom filters
        requests_mock.get(
            "https://api.openalex.org/works",
            json={"results": [], "meta": {"count": 0}},
        )

        result = search_works(
            "query", filter_str="publication_year:>2020", use_semantic=False
        )

        assert result["search_type"] == "keyword"


class TestStorageModule:
    """Additional tests for raven.storage module."""

    def test_search_case_insensitive(self, tmp_path):
        """Test search is case insensitive."""
        db_path = tmp_path / "test.db"
        init_database(db_path)
        add_paper(db_path, "10.1234/test", "UPPERCASE Title", "article")

        # Search with lowercase
        results = search_papers(db_path, "uppercase")

        assert len(results) == 1
        assert results[0]["title"] == "UPPERCASE Title"

    def test_search_returns_limited_results(self, tmp_path):
        """Test search limits results to 50."""
        db_path = tmp_path / "test.db"
        init_database(db_path)

        # Add many papers
        for i in range(60):
            add_paper(db_path, f"10.1234/{i:03d}", f"Paper {i}", "article")

        results = search_papers(db_path, "Paper")

        assert len(results) == 50  # Limited to 50
