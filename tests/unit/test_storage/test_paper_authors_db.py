"""DB-backed tests for paper_authors module.

Run with: pytest tests/unit/test_storage/test_paper_authors_db.py -v
"""

import sqlite3

from raven.storage.paper_authors import (
    add_author,
    add_paper_authors,
    delete_paper_authors,
    get_paper_authors,
)


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
