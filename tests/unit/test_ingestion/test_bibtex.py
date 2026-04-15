"""Unit tests for BibTeX parsing functionality.

Run with: pytest tests/unit/test_ingestion/test_bibtex.py -v
"""

from raven.ingestion.bibtex import filter_valid_entries


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

        entries = [{"doi": "10.1234/test", "title": "Paper 1"}]
        valid, invalid = filter_valid_entries(entries)

        assert valid[0].get("_identifier") == "doi:10.1234/test"

    def test_filter_valid_entries_empty_list(self):
        """filter_valid_entries handles empty list."""

        valid, invalid = filter_valid_entries([])

        assert len(valid) == 0
        assert len(invalid) == 0
