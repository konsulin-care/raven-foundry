"""Unit tests for raven.storage module.

Run with: pytest tests/test_storage.py -v
"""

import sqlite3

import pytest

from raven.storage import (
    _safe_add_column,
    add_embedding,
    add_paper,
    extract_identifier,
    get_paper_id_by_doi,
    get_paper_id_by_identifier,
    init_database,
    search_by_embedding,
    search_papers,
    serialize_f32,
)


class TestSerializeF32:
    """Tests for serialize_f32 function."""

    def test_serialize_f32_384_dimensions(self):
        """serialize_f32 correctly serializes 384-dimensional vector."""
        vector = [0.1] * 384
        result = serialize_f32(vector)

        assert isinstance(result, bytes)

    def test_serialize_f32_output_length(self):
        """serialize_f32 outputs correct byte length for 384-dim vector."""
        vector = [0.1] * 384
        result = serialize_f32(vector)

        # Each float is 4 bytes (float32), so 384 * 4 = 1536 bytes
        expected_length = 384 * 4
        assert len(result) == expected_length

    def test_serialize_f32_custom_dimensions(self):
        """serialize_f32 handles different vector dimensions."""
        vector = [0.5, 0.3, 0.2, 0.1]
        result = serialize_f32(vector)

        expected_length = 4 * 4  # 4 floats * 4 bytes each
        assert len(result) == expected_length

    def test_serialize_f32_zero_values(self):
        """serialize_f32 correctly serializes zeros."""
        vector = [0.0] * 384
        result = serialize_f32(vector)

        assert isinstance(result, bytes)
        assert len(result) == 384 * 4

    def test_serialize_f32_negative_values(self):
        """serialize_f32 correctly serializes negative floats."""
        vector = [-0.5, -0.3, 0.0, 0.3]
        result = serialize_f32(vector)

        assert isinstance(result, bytes)
        assert len(result) == 16  # 4 floats * 4 bytes


class TestSafeAddColumn:
    """Tests for _safe_add_column helper function."""

    @pytest.fixture
    def conn(self, tmp_path):
        """Create test database with papers table."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            )
        """)
        conn.commit()
        yield conn
        conn.close()

    def test_safe_add_column_valid(self, conn):
        """_safe_add_column adds valid column."""
        _safe_add_column(conn, "authors", "TEXT")

        # Verify column was added
        cursor = conn.execute("PRAGMA table_info(papers)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "authors" in columns

    def test_safe_add_column_invalid_raises(self, conn):
        """_safe_add_column raises for invalid column name."""
        with pytest.raises(ValueError, match="Invalid column name"):
            _safe_add_column(conn, "malicious_column", "TEXT")

    def test_safe_add_column_abstract_type(self, conn):
        """_safe_add_column handles abstract column type."""
        _safe_add_column(conn, "abstract", "TEXT")

        cursor = conn.execute("PRAGMA table_info(papers)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "abstract" in columns


class TestInitDatabase:
    """Tests for init_database function."""

    def test_init_database_runs_without_error(self, tmp_path, mocker):
        """init_database executes without raising exceptions."""
        db_path = tmp_path / "test.db"

        # Mock the vector extension loader to avoid requiring native extension in tests
        mocker.patch("raven.storage._load_vector_extension")
        init_database(db_path)

    def test_init_database_creates_db_file(self, tmp_path, mocker):
        """init_database creates the database file."""
        db_path = tmp_path / "test.db"

        # Mock the vector extension loader to avoid requiring native extension in tests
        mocker.patch("raven.storage._load_vector_extension")
        init_database(db_path)

        # Database file should exist
        assert db_path.exists()

    def test_init_database_creates_valid_columns(self, tmp_path, mocker):
        """init_database creates tables with expected columns."""
        db_path = tmp_path / "test.db"

        # Mock the vector extension loader
        mocker.patch("raven.storage._load_vector_extension")
        init_database(db_path)

        # Verify expected columns exist
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(papers)")
            columns = {row[1] for row in cursor.fetchall()}

        expected_columns = {
            "id",
            "identifier",
            "title",
            "authors",
            "abstract",
            "publication_year",
            "venue",
            "type",
            "created_at",
            "openalex_id",
        }
        assert expected_columns.issubset(columns)


class TestDatabaseWithFixture:
    """Tests using a shared fixture that sets up database properly for testing.

    This fixture creates the database WITHOUT the vec0 virtual table,
    using a regular table instead for embedding storage.
    """

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create a test database with all tables (excluding vec0)."""
        db_path = tmp_path / "test.db"

        # Create tables manually (skipping vec0 virtual table)
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_type ON papers(type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_papers_title ON papers(title)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(publication_year)"
            )
            # Use regular table instead of vec0 for testing
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()

        return db_path

    def test_papers_table_columns(self, db_path):
        """Verify papers table has expected columns."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA table_info(papers)")
            columns = {row[1] for row in cursor.fetchall()}

        expected = {
            "id",
            "identifier",
            "title",
            "authors",
            "abstract",
            "publication_year",
            "venue",
            "type",
            "created_at",
            "openalex_id",
        }
        assert expected.issubset(columns)

    def test_indexes_created(self, db_path):
        """Verify required indexes exist."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = {row[0] for row in cursor.fetchall()}

        expected = {
            "idx_papers_identifier",
            "idx_papers_type",
            "idx_papers_title",
            "idx_papers_year",
        }
        assert expected.issubset(indexes)


class TestAddPaperWithFixture:
    """Tests for add_paper using the test fixture."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema matching production."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier COLLATE NOCASE)"
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_add_paper_returns_paper_id(self, db_path):
        """add_paper returns the ID of the newly inserted paper."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
            authors="John Doe",
            publication_year=2024,
        )

        assert isinstance(paper_id, int)
        assert paper_id > 0

    def test_add_paper_with_minimal_fields(self, db_path):
        """add_paper works with only required fields."""
        paper_id = add_paper(
            db_path=db_path,
            identifier=None,
            title="Minimal Test Paper",
        )

        assert isinstance(paper_id, int)
        assert paper_id > 0

    def test_add_paper_duplicate_identifier_raises(self, db_path):
        """add_paper raises ValueError for duplicate identifier."""
        # Add first paper
        add_paper(
            db_path=db_path,
            identifier="doi:10.1234/duplicate",
            title="Original Paper",
        )

        # Try to add duplicate - identifier has UNIQUE constraint
        with pytest.raises((ValueError, sqlite3.IntegrityError)):
            add_paper(
                db_path=db_path,
                identifier="doi:10.1234/duplicate",
                title="Duplicate Paper",
            )

    def test_add_paper_stores_all_fields(self, db_path):
        """add_paper correctly stores all provided fields."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/full",
            title="Full Test Paper",
            authors="John Doe, Jane Smith",
            abstract="Test abstract",
            publication_year=2024,
            venue="Test Journal",
            openalex_id="https://openalex.org/W123",
            paper_type="article",
        )

        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM papers WHERE id = ?", (paper_id,))
            row = dict(cursor.fetchone())

        assert row["identifier"] == "doi:10.1234/full"
        assert row["title"] == "Full Test Paper"
        assert row["authors"] == "John Doe, Jane Smith"
        assert row["abstract"] == "Test abstract"
        assert row["publication_year"] == 2024
        assert row["venue"] == "Test Journal"
        assert row["openalex_id"] == "https://openalex.org/W123"
        assert row["type"] == "article"


class TestSearchPapersWithFixture:
    """Tests for search_papers using the test fixture."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier)"
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_search_papers_by_title(self, db_path):
        """search_papers finds papers by title."""
        add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Machine Learning Advances",
        )

        results = search_papers(db_path, "machine learning")

        assert len(results) == 1
        assert results[0]["title"] == "Machine Learning Advances"

    def test_search_papers_by_identifier(self, db_path):
        """search_papers finds papers by identifier."""
        add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        results = search_papers(db_path, "10.1234")

        assert len(results) == 1
        assert results[0]["identifier"] == "doi:10.1234/test"

    def test_search_papers_no_results(self, db_path):
        """search_papers returns empty list when no matches."""
        results = search_papers(db_path, "nonexistent")

        assert results == []


class TestGetPaperIdByIdentifier:
    """Tests for get_paper_id_by_identifier function."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with papers table."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT NOT NULL COLLATE NOCASE,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        return db_path

    def test_get_paper_id_by_identifier_returns_id(self, db_path):
        """get_paper_id_by_identifier returns correct paper ID."""
        # Add a paper first
        paper_id = add_paper(db_path, identifier="doi:10.1234/test", title="Test Paper")

        # Lookup by identifier
        result = get_paper_id_by_identifier(db_path, "doi:10.1234/test")

        assert result == paper_id

    def test_get_paper_id_by_identifier_case_insensitive(self, db_path):
        """get_paper_id_by_identifier is case-insensitive."""
        add_paper(db_path, identifier="doi:10.1234/Test", title="Test Paper")

        # Lookup with different case
        result = get_paper_id_by_identifier(db_path, "doi:10.1234/test")

        assert result is not None

    def test_get_paper_id_by_identifier_not_found(self, db_path):
        """get_paper_id_by_identifier returns None for non-existent identifier."""
        result = get_paper_id_by_identifier(db_path, "doi:10.1234/nonexistent")

        assert result is None

    def test_get_paper_id_by_identifier_none_input(self, db_path):
        """get_paper_id_by_identifier returns None for None input."""
        result = get_paper_id_by_identifier(db_path, None)

        assert result is None

    def test_get_paper_id_by_doi_backward_compatible(self, db_path):
        """get_paper_id_by_doi still works for backward compatibility."""
        # Add a paper first
        paper_id = add_paper(db_path, identifier="doi:10.1234/test", title="Test Paper")

        # Lookup by DOI using backward compatible function
        result = get_paper_id_by_doi(db_path, "10.1234/test")

        assert result == paper_id


class TestAddEmbeddingWithFixture:
    """Tests for add_embedding using the test fixture."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_add_embedding_valid_paper(self, db_path):
        """add_embedding adds embedding for valid paper_id."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        embedding = [0.1] * 384

        # Should not raise ValueError
        add_embedding(db_path, paper_id, embedding)

    def test_add_embedding_dimension_mismatch(self, db_path):
        """add_embedding raises ValueError for wrong dimension."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        # Wrong dimension (not 384)
        wrong_embedding = [0.1] * 256

        with pytest.raises(ValueError, match="dimension mismatch"):
            add_embedding(db_path, paper_id, wrong_embedding)

    def test_add_embedding_dimension_383_raises(self, db_path):
        """add_embedding raises for 383-dimensional vector."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        wrong_embedding = [0.1] * 383

        with pytest.raises(ValueError, match="dimension mismatch"):
            add_embedding(db_path, paper_id, wrong_embedding)

    def test_add_embedding_dimension_385_raises(self, db_path):
        """add_embedding raises for 385-dimensional vector."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        wrong_embedding = [0.1] * 385

        with pytest.raises(ValueError, match="dimension mismatch"):
            add_embedding(db_path, paper_id, wrong_embedding)


class TestSearchByEmbeddingDimension:
    """Tests for search_by_embedding dimension validation.

    These tests verify dimension checking without requiring vec0.
    """

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_search_by_embedding_dimension_mismatch(self, db_path):
        """search_by_embedding raises ValueError for wrong dimension."""
        wrong_embedding = [0.1] * 256

        with pytest.raises(ValueError, match="dimension mismatch"):
            search_by_embedding(db_path, wrong_embedding)

    def test_search_by_embedding_dimension_383_raises(self, db_path):
        """search_by_embedding raises for 383 dimensions."""
        wrong_embedding = [0.1] * 383

        with pytest.raises(ValueError, match="dimension mismatch"):
            search_by_embedding(db_path, wrong_embedding)

    def test_search_by_embedding_dimension_385_raises(self, db_path):
        """search_by_embedding raises for 385 dimensions."""
        wrong_embedding = [0.1] * 385

        with pytest.raises(ValueError, match="dimension mismatch"):
            search_by_embedding(db_path, wrong_embedding)


class TestSearchByEmbeddingWithFixture:
    """Tests for search_by_embedding using mocked vec functionality.

    These tests verify the function builds correct SQL but may not
    get full results without vec0 extension.
    """

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database with full schema."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_search_by_embedding_returns_list(self, db_path):
        """search_by_embedding returns a list or skips if vec0 unavailable."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        # Add embedding manually
        embedding = serialize_f32([0.1] * 384)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO embeddings (paper_id, embedding) VALUES (?, ?)",
                (paper_id, embedding),
            )
            conn.commit()

        query = [0.1] * 384

        # The vec0 extension provides e.distance column which doesn't exist
        # in our regular table, so this will fail - that's expected
        try:
            results = search_by_embedding(db_path, query, top_k=10)
            # If it works, verify it's a list
            assert isinstance(results, list)
        except sqlite3.OperationalError as e:
            if "no such column: e.distance" in str(e):
                pytest.skip("vec0 extension not available")
            raise

    def test_search_by_embedding_result_fields(self, db_path):
        """search_by_embedding result contains expected fields."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
        )

        embedding = serialize_f32([0.1] * 384)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "INSERT INTO embeddings (paper_id, embedding) VALUES (?, ?)",
                (paper_id, embedding),
            )
            conn.commit()

        query = [0.1] * 384

        # The vec0 extension provides e.distance column which doesn't exist
        # in our regular table, so this will fail - that's expected
        try:
            results = search_by_embedding(db_path, query, top_k=1)
            if results:
                result = results[0]
                # Check structure if results returned
                assert "id" in result
                assert "distance" in result
        except sqlite3.OperationalError as e:
            if "no such column: e.distance" in str(e):
                pytest.skip("vec0 extension not available")
            raise


class TestIntegrationWithFixture:
    """Integration tests combining multiple functions."""

    @pytest.fixture
    def db_path(self, tmp_path):
        """Create test database."""
        db_path = tmp_path / "test.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    openalex_id TEXT UNIQUE,
                    identifier TEXT COLLATE NOCASE NOT NULL,
                    title TEXT NOT NULL,
                    authors TEXT,
                    abstract TEXT,
                    publication_year INTEGER,
                    venue TEXT,
                    type TEXT DEFAULT 'article',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_papers_identifier ON papers(identifier)"
            )
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    paper_id INTEGER PRIMARY KEY,
                    embedding BLOB
                )
            """)
            conn.commit()
        return db_path

    def test_add_paper_and_retrieve(self, db_path):
        """Add paper and retrieve it."""
        paper_id = add_paper(
            db_path=db_path,
            identifier="doi:10.1234/test",
            title="Test Paper",
            authors="Test Author",
            publication_year=2024,
        )

        results = search_papers(db_path, "test")

        assert len(results) == 1
        assert results[0]["id"] == paper_id

    def test_add_multiple_papers(self, db_path):
        """Add multiple papers with different identifiers."""
        paper_ids = []
        for i in range(3):
            pid = add_paper(
                db_path=db_path,
                identifier=f"doi:10.1234/test{i}",
                title=f"Paper {i}",
            )
            paper_ids.append(pid)

        assert len(paper_ids) == 3
        assert len(set(paper_ids)) == 3  # All unique

    def test_search_empty_db(self, db_path):
        """Search on empty database returns empty list."""
        results = search_papers(db_path, "anything")

        assert results == []


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


class TestDoiToIdentifierMigration:
    """Tests for doi->identifier schema migration.

    This tests the fix for the bug where the migration logic captured
    existing_columns AFTER adding new columns, causing the doi migration
    to fail silently and leave a NOT NULL constraint on the old doi column.
    """

    def test_migration_with_old_doi_column(self, tmp_path):
        """init_database migrates old doi column to identifier correctly.

        Simulates a database with the old schema (doi column) and verifies
        that init_database() properly migrates data to the new identifier column
        and drops the old doi column.
        """
        db_path = tmp_path / "test.db"

        # Create database with old schema (has doi column with NOT NULL constraint)
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY,
                doi TEXT NOT NULL,
                title TEXT NOT NULL
            )
        """)
        # Insert test data
        conn.execute(
            "INSERT INTO papers (doi, title) VALUES (?, ?)",
            ("10.1234/test", "Test Paper"),
        )
        conn.commit()
        conn.close()

        # Run init_database to trigger migration
        init_database(db_path)

        # Verify: doi column should be dropped, identifier should have data
        conn = sqlite3.connect(db_path)
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(papers)").fetchall()
        }

        assert "doi" not in columns, "doi column should be dropped after migration"
        assert "identifier" in columns, "identifier column should exist"

        # Verify data was migrated
        result = conn.execute("SELECT identifier FROM papers WHERE id = 1").fetchone()
        assert result is not None
        assert result[0] == "doi:10.1234/test", (
            "DOI should be migrated with doi: prefix"
        )

        conn.close()

    def test_migration_idempotent_no_doi_column(self, tmp_path):
        """init_database handles database without doi column correctly.

        Verifies that databases without the old doi column don't trigger
        the migration and work correctly.
        """
        db_path = tmp_path / "test.db"

        # Run init_database on fresh database
        init_database(db_path)

        # Verify: identifier column exists, no doi column
        conn = sqlite3.connect(db_path)
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(papers)").fetchall()
        }

        assert "identifier" in columns
        assert "doi" not in columns

        conn.close()

    def test_migration_with_null_doi_values(self, tmp_path):
        """init_database handles NULL doi values during migration."""
        db_path = tmp_path / "test.db"

        # Create database with old schema and NULL doi values
        conn = sqlite3.connect(db_path)
        conn.execute("""
            CREATE TABLE papers (
                id INTEGER PRIMARY KEY,
                doi TEXT,
                title TEXT NOT NULL
            )
        """)
        # Insert record with NULL doi
        conn.execute(
            "INSERT INTO papers (doi, title) VALUES (NULL, ?)", ("No DOI Paper",)
        )
        conn.commit()
        conn.close()

        # Run init_database to trigger migration
        init_database(db_path)

        # Verify: record with NULL doi should have empty/null identifier
        conn = sqlite3.connect(db_path)
        result = conn.execute("SELECT identifier FROM papers WHERE id = 1").fetchone()
        # NULL doi values are skipped in migration (WHERE doi IS NOT NULL AND doi != '')
        assert result[0] is None or result[0] == ""

        conn.close()
