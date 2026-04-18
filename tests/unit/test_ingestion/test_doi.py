"""Unit tests for DOI normalization functions.

Run with: pytest tests/unit/test_ingestion/test_doi.py -v
"""

from raven.ingestion import normalize_doi, normalize_identifier


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
        assert normalize_identifier("doi:10.1234/test") == "doi:10.1234/test"

    def test_doi_without_prefix(self):
        """normalize_identifier adds doi: prefix to bare DOI."""
        assert normalize_identifier("10.1234/test") == "doi:10.1234/test"

    def test_doi_url(self):
        """normalize_identifier handles DOI URL."""
        assert (
            normalize_identifier("https://doi.org/10.1234/test") == "doi:10.1234/test"
        )

    def test_openalex_with_explicit_prefix(self):
        """normalize_identifier handles explicit openalex: prefix."""
        assert normalize_identifier("openalex:W7119934875") == "openalex:w7119934875"

    def test_openalex_bare_id(self):
        """normalize_identifier handles bare OpenAlex ID."""
        assert normalize_identifier("W7119934875") == "openalex:W7119934875"

    def test_openalex_url(self):
        """normalize_identifier handles OpenAlex URL."""
        assert (
            normalize_identifier("https://openalex.org/W7119934875")
            == "openalex:w7119934875"
        )

    def test_pmid_with_explicit_prefix(self):
        """normalize_identifier handles explicit pmid: prefix."""
        assert normalize_identifier("pmid:29456894") == "pmid:29456894"

    def test_pmid_bare_id(self):
        """normalize_identifier treats 7+ digits as PMID."""
        assert normalize_identifier("29456894") == "pmid:29456894"

    def test_pmid_url(self):
        """normalize_identifier handles PubMed URL."""
        assert (
            normalize_identifier("https://pubmed.ncbi.nlm.nih.gov/29456894")
            == "pmid:29456894"
        )

    def test_mag_with_prefix(self):
        """normalize_identifier handles explicit mag: prefix."""
        assert normalize_identifier("mag:2741809807") == "mag:2741809807"

    def test_short_digits_as_mag(self):
        """normalize_identifier treats short digits (1-6) as MAG."""
        # 6 digits or less is treated as MAG (less common for PMID)
        assert normalize_identifier("123456") == "mag:123456"
