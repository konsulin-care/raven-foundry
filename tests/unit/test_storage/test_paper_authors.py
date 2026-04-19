"""Unit tests for paper_authors module.

Run with: pytest tests/unit/test_storage/test_paper_authors.py -v
"""

from raven.storage.paper_authors import convert_authors_to_data


class TestConvertAuthorsToData:
    """Tests for convert_authors_to_data function."""

    def test_with_single_author(self):
        """Single author gets converted correctly."""
        result = convert_authors_to_data("John Smith")
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "John Smith"
        assert result[0]["orcid"] is None
        assert result[0]["is_corresponding"] == 0
        assert result[0]["order"] == 0
        assert result[0]["id"].startswith("A")

    def test_with_multiple_authors(self):
        """Multiple authors get converted with correct ordering."""
        result = convert_authors_to_data("John Smith, Jane Doe, Bob Wilson")
        assert result is not None
        assert len(result) == 3
        assert result[0]["name"] == "John Smith"
        assert result[1]["name"] == "Jane Doe"
        assert result[2]["name"] == "Bob Wilson"
        assert result[0]["order"] == 0
        assert result[1]["order"] == 1
        assert result[2]["order"] == 2

    def test_with_none_returns_none(self):
        """None input returns None."""
        result = convert_authors_to_data(None)
        assert result is None

    def test_with_empty_string_returns_none(self):
        """Empty string returns None."""
        result = convert_authors_to_data("")
        assert result is None

    def test_with_whitespace_only_returns_empty_list(self):
        """Whitespace-only string returns empty list."""
        result = convert_authors_to_data("   ")
        assert result == []

    def test_with_extra_whitespace(self):
        """Extra whitespace in names is trimmed."""
        result = convert_authors_to_data("  John Smith  ,  Jane Doe  ")
        assert result is not None
        assert len(result) == 2
        assert result[0]["name"] == "John Smith"
        assert result[1]["name"] == "Jane Doe"

    def test_ids_are_uuid5_based(self):
        """Verify IDs are UUID5 based (36 char UUID after A)."""
        result = convert_authors_to_data("John Smith")
        author_id = result[0]["id"]
        assert author_id.startswith("A")
        uuid_part = author_id[1:]
        assert len(uuid_part) == 36
        assert uuid_part.count("-") == 4  # UUID5 format with 4 hyphens

    def test_idempotency(self):
        """Same author name produces same ID consistently."""
        result1 = convert_authors_to_data("John Smith")
        result2 = convert_authors_to_data("John Smith")
        assert result1[0]["id"] == result2[0]["id"]
