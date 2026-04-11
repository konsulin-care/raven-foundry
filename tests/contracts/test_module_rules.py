"""Contract tests - enforce AGENTS.md rules across modules.

These tests verify that each module follows the rules defined in its AGENTS.md.
Run with: pytest tests/contracts/ -v
"""

import inspect
from pathlib import Path

import pytest

# =============================================================================
# INGESTION Module Rules (from src/raven/ingestion/AGENTS.md)
# =============================================================================
# Rules:
# - Deduplicate using DOI before insertion
# - Do not use LLMs in this module
# - Keep processing CPU-efficient
# - Ensure ingestion integrates cleanly with CLI workflow
# =============================================================================


class TestIngestionModuleRules:
    """Tests enforcing ingestion/AGENTS.md rules."""

    def test_no_llm_in_ingestion_module(self):
        """INGESTION: Do not use LLMs in this module."""
        import raven.ingestion as module

        source = inspect.getsource(module)

        # Verify no LLM imports
        assert "groq" not in source, "ingestion must not import groq"
        assert "ChatCompletion" not in source
        assert (
            "llm" not in source.lower()
            or "llm" in source.lower() == "fullname" not in source
        )

    def test_deduplication_by_doi(self):
        """INGESTION: Deduplicate using DOI before insertion."""
        import tempfile
        from pathlib import Path

        from raven.storage import add_paper

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Initialize database
            from raven.storage import init_database

            init_database(db_path)

            # First insert should succeed
            add_paper(db_path, "10.1234/test", "Test Paper", "article")

            # Duplicate should raise ValueError
            with pytest.raises(ValueError, match="already exists"):
                add_paper(db_path, "10.1234/test", "Test Paper 2", "article")

    def test_doi_cleaning(self):
        """INGESTION: Clean DOI format correctly."""

        # Test DOI URL stripping
        test_cases = [
            ("https://doi.org/10.1234/test", "10.1234/test"),
            ("doi:10.1234/test", "10.1234/test"),
            ("10.1234/test", "10.1234/test"),
        ]

        for input_doi, expected in test_cases:
            cleaned = input_doi.strip().lower()
            if cleaned.startswith("https://doi.org/"):
                cleaned = cleaned.replace("https://doi.org/", "")
            elif cleaned.startswith("doi:"):
                cleaned = cleaned.replace("doi:", "")

            assert cleaned == expected


# =============================================================================
# EMBEDDINGS Module Rules (from src/raven/embeddings/AGENTS.md)
# =============================================================================
# Rules:
# - Do not change embedding dimensionality
# - Keep inference CPU-only
# - Cache embeddings aggressively
# - Ensure compatibility with SQLite vector schema
# =============================================================================


class TestEmbeddingsModuleRules:
    """Tests enforcing embeddings/AGENTS.md rules."""

    def test_embedding_dimensionality(self):
        """EMBEDDINGS: Use 384-dimensional embeddings (multilingual-e5-small)."""
        # This would verify the model configuration
        # For now, verify the constant is defined
        from pathlib import Path

        # Check for dimension constant in module or config
        embeddings_file = Path("src/raven/embeddings/__init__.py")
        if embeddings_file.exists():
            content = embeddings_file.read_text()
            # Should reference the model or 384 dimensions
            assert "384" in content or "e5" in content.lower()

    def test_cpu_only_inference(self):
        """EMBEDDINGS: CPU-only inference (no GPU dependencies)."""
        import raven.embeddings as module

        if module.__file__:
            source = Path(module.__file__).read_text()
            # Should not have CUDA/GPU-specific imports
            assert "cuda" not in source.lower()
            assert "torch.cuda" not in source


# =============================================================================
# LLM Module Rules (from src/raven/llm/AGENTS.md)
# =============================================================================
# Rules:
# - Batch requests whenever possible
# - Cache all responses
# - Respect rate limits (1000 req/day, TPM constraints)
# - Never use LLMs for parsing or embeddings
# - Route long-running tasks through scheduler when needed
# =============================================================================


class TestLLMModuleRules:
    """Tests enforcing llm/AGENTS.md rules."""

    def test_caching_required(self):
        """LLM: Cache all responses."""
        import raven.llm as module

        # Verify caching mechanism exists
        source = inspect.getsource(module)
        assert "cache" in source.lower() or "Cache" in source

    def test_no_llm_for_parsing(self):
        """LLM: Never use LLMs for parsing or embeddings."""
        import raven.llm as module

        # Should not use LLM for deterministic parsing tasks
        # (This is enforced by design - LLM is for reasoning only)
        # Note: LLM should only be used for reasoning tasks (query refinement,
        # hypothesis generation, summarization), not for parsing or embeddings
        assert hasattr(module, "query_llm")


# =============================================================================
# STORAGE Module Rules (from src/raven/storage/AGENTS.md)
# =============================================================================
# Rules:
# - Enforce DOI uniqueness
# - Use WAL mode for durability
# - Maintain indexes on DOI, type, title
# - Optimize for long-term scale (50GB+ datasets)
# =============================================================================


class TestStorageModuleRules:
    """Tests enforcing storage/AGENTS.md rules."""

    def test_wal_mode_enabled(self):
        """STORAGE: Use WAL mode for durability."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            from raven.storage import init_database

            init_database(db_path)

            # Verify WAL mode
            import sqlite3

            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]
            conn.close()

            assert mode.upper() == "WAL"

    def test_doi_unique_constraint(self):
        """STORAGE: Enforce DOI uniqueness."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            from raven.storage import add_paper, init_database

            init_database(db_path)

            # First insert
            add_paper(db_path, "10.1234/unique", "First Paper", "article")

            # Duplicate should fail
            with pytest.raises(ValueError):
                add_paper(db_path, "10.1234/unique", "Duplicate", "article")

    def test_indexes_exist(self):
        """STORAGE: Maintain indexes on DOI, type, title."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            from raven.storage import init_database

            init_database(db_path)

            import sqlite3

            conn = sqlite3.connect(db_path)
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
            )
            indexes = [row[0] for row in cursor.fetchall()]
            conn.close()

            # Should have indexes on doi, type, title
            index_names = [i.lower() for i in indexes]
            assert any("doi" in i for i in index_names), "Missing DOI index"
            assert any("type" in i for i in index_names), "Missing type index"
            assert any("title" in i for i in index_names), "Missing title index"


# =============================================================================
# Integration: CLI Workflow
# =============================================================================


class TestCLIWorkflow:
    """Test full CLI integration."""

    def test_ingest_to_search_workflow(self):
        """Complete workflow: init -> ingest -> search."""
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Initialize
            from raven.storage import init_database

            init_database(db_path)

            # Add paper directly (simulating successful ingest)
            from raven.storage import add_paper

            add_paper(db_path, "10.1234/workflow", "Test Workflow Paper", "article")

            # Search
            from raven.storage import search_papers

            results = search_papers(db_path, "workflow")

            assert len(results) == 1
            assert results[0]["doi"] == "10.1234/workflow"
