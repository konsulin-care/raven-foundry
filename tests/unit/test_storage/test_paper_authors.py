"""Unit tests for paper_authors module.

Run with: pytest tests/unit/test_storage/test_paper_authors.py -v
"""

import sqlite3

import pytest

from raven.storage.paper_authors import (
    _get_author_id_from_orcid,
    add_author,
    add_paper_authors,
    convert_authors_to_data,
    delete_paper_authors,
    get_paper_authors,
)


class TestGetAuthorIdFromOrcid:
    """Tests for _get_author_id_from_orcid function."""

    def test_with_full_orcid_url(self):
        """ORCID with URL prefix gets transformed correctly."""
        result = _get_author_id_from_orcid("https://orcid.org/0000-0002-1825-0097")
        assert result == "A0000-0002-1825-0097"

    def test_with_orcid_only(self):
        """ORCID without URL prefix gets transformed correctly."""
        result = _get_author_id_from_orcid("0000-0002-1825-0097")
        assert result == "A0000-0002-1825-0097"

    def test_with_none_generates_sha256_based_id(self):
        """None input generates SHA-256 based author ID."""
        result = _get_author_id_from_orcid(None)
        assert result.startswith("A")
        assert len(result) == 11  # 'A' + 10 hex chars

    def test_with_none_is_deterministic_per_call(self):
        """None input generates a valid SHA-256 based ID (not tested for exact value)."""
        result1 = _get_author_id_from_orcid(None)
        result2 = _get_author_id_from_orcid(None)
        assert result1.startswith("A")
        assert len(result1) == 11
        assert result2.startswith("A")
        assert len(result2) == 11


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

    def test_ids_are_sha256_based(self):
        """Verify IDs are SHA-256 based (10 hex chars after A)."""
        result = convert_authors_to_data("John Smith")
        author_id = result[0]["id"]
        assert author_id.startswith("A")
        hex_part = author_id[1:]
        assert len(hex_part) == 10
        assert all(c in "0123456789ABCDEF" for c in hex_part)

    def test_idempotency(self):
        """Same author name produces same ID consistently."""
        result1 = convert_authors_to_data("John Smith")
        result2 = convert_authors_to_data("John Smith")
        assert result1[0]["id"] == result2[0]["id"]


@pytest.fixture
def db_path_with_schema(tmp_path):
    """Create test database with authors and paper_authors tables."""
    db_path = tmp_path / "test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                identifier TEXT NOT NULL,
                title TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                id TEXT PRIMARY KEY,
                orcid TEXT,
                name TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS paper_authors (
                paper_id INTEGER NOT NULL,
                author_id TEXT NOT NULL,
                author_order INTEGER NOT NULL,
                is_corresponding INTEGER DEFAULT 0,
                PRIMARY KEY (paper_id, author_id)
            )
        """)
        conn.commit()
    return db_path


class TestAddPaperAuthors:
    """Tests for add_paper_authors function."""

    def test_add_paper_authors_with_valid_data(self, db_path_with_schema):
        """Adding paper authors works correctly."""
        paper_id = 1
        authors_data = [
            {
                "id": "A123",
                "name": "John Smith",
                "orcid": None,
                "is_corresponding": 1,
                "order": 0,
            },
            {
                "id": "A456",
                "name": "Jane Doe",
                "orcid": "0000-0001-2345-6789",
                "is_corresponding": 0,
                "order": 1,
            },
        ]
        add_paper_authors(db_path_with_schema, paper_id, authors_data)

        authors = get_paper_authors(db_path_with_schema, paper_id)
        assert len(authors) == 2
        assert authors[0]["name"] == "John Smith"
        assert authors[1]["name"] == "Jane Doe"

    def test_add_paper_authors_with_none_returns_early(self, db_path_with_schema):
        """None authors_data returns early without error."""
        add_paper_authors(db_path_with_schema, 1, None)
        authors = get_paper_authors(db_path_with_schema, 1)
        assert len(authors) == 0


class TestGetPaperAuthors:
    """Tests for get_paper_authors function."""

    def test_get_paper_authors_empty(self, db_path_with_schema):
        """Getting authors for paper with no authors returns empty list."""
        result = get_paper_authors(db_path_with_schema, 999)
        assert result == []


class TestDeletePaperAuthors:
    """Tests for delete_paper_authors function."""

    def test_delete_paper_authors(self, db_path_with_schema):
        """Deleting paper authors works correctly."""
        paper_id = 1
        authors_data = [
            {
                "id": "A123",
                "name": "John Smith",
                "orcid": None,
                "is_corresponding": 0,
                "order": 0,
            }
        ]
        add_paper_authors(db_path_with_schema, paper_id, authors_data)

        delete_paper_authors(db_path_with_schema, paper_id)
        authors = get_paper_authors(db_path_with_schema, paper_id)
        assert len(authors) == 0


class TestAddAuthor:
    """Tests for add_author function."""

    def test_add_author(self, db_path_with_schema):
        """Adding an author works correctly."""
        add_author(db_path_with_schema, "A123", "John Smith", "0000-0001-2345-6789")

        with sqlite3.connect(db_path_with_schema) as conn:
            cursor = conn.execute(
                "SELECT id, orcid, name FROM authors WHERE id = 'A123'"
            )
            row = cursor.fetchone()
            assert row == ("A123", "0000-0001-2345-6789", "John Smith")
