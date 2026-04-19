"""Unit tests for extract_identifier helper function.

Run with: pytest tests/unit/test_storage/test_extract.py -v
"""

from raven.storage import extract_identifier


class TestExtractIdentifier:
    """Tests for extract_identifier helper function."""

    def test_extract_identifier_doi_priority(self):
        """extract_identifier returns doi: prefix when doi exists."""
        ids = {
            "openalex": "https://openalex.org/W2741809807",
            "doi": "https://doi.org/10.5281/zenodo.18201069",
            "mag": "2741809807",
            "pmid": "https://pubmed.ncbi.nlm.nih.gov/29456894",
        }

        result = extract_identifier(ids)

        assert result == "doi:10.5281/zenodo.18201069"

    def test_extract_identifier_openalex_fallback(self):
        """extract_identifier returns openalex: prefix when no doi but openalex exists."""
        ids = {
            "openalex": "https://openalex.org/W2741809807",
            "mag": "2741809807",
            "pmid": "https://pubmed.ncbi.nlm.nih.gov/29456894",
        }

        result = extract_identifier(ids)

        assert result == "openalex:W2741809807"

    def test_extract_identifier_pmid_fallback(self):
        """extract_identifier returns pmid: prefix when no doi/openalex but pmid exists."""
        ids = {
            "mag": "2741809807",
            "pmid": "https://pubmed.ncbi.nlm.nih.gov/29456894",
        }

        result = extract_identifier(ids)

        assert result == "pmid:29456894"

    def test_extract_identifier_pmcid_fallback(self):
        """extract_identifier returns pmcid: prefix when no doi/openalex/pmid but pmcid exists."""
        ids = {
            "mag": "2741809807",
            "pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC1234567",
        }

        result = extract_identifier(ids)

        assert result == "pmcid:1234567"

    def test_extract_identifier_mag_fallback(self):
        """extract_identifier returns mag: prefix when no doi/openalex/pmid but mag exists."""
        ids = {"mag": "2741809807"}

        result = extract_identifier(ids)

        assert result == "mag:2741809807"

    def test_extract_identifier_no_ids(self):
        """extract_identifier returns None when no IDs available."""
        ids = {}

        result = extract_identifier(ids)

        assert result is None

    def test_extract_identifier_none_input(self):
        """extract_identifier returns None for None input."""
        result = extract_identifier(None)

        assert result is None

    def test_extract_identifier_doi_http_variant(self):
        """extract_identifier handles http://doi.org/ variant."""
        ids = {"doi": "http://doi.org/10.1234/test"}

        result = extract_identifier(ids)

        assert result == "doi:10.1234/test"
