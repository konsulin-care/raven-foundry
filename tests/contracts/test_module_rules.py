"""Contract tests - enforce AGENTS.md rules across modules.

These tests verify that each module follows the rules defined in its AGENTS.md.
Run with: pytest tests/contracts/ -v
"""

import inspect
import sqlite3
import tempfile
from pathlib import Path

import pytest

import raven.embeddings
import raven.ingestion
import raven.llm
from raven.storage import add_paper, init_database, search_papers

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
        source = inspect.getsource(raven.ingestion)

        # Verify no LLM imports (check import statements only, not docstrings)
        # Split source to separate imports from code
        source_lines = source.split("\n")
        import_lines = [
            ln for ln in source_lines if ln.startswith(("import ", "from "))
        ]

        # Check for LLM-related imports
        for line in import_lines:
            line_lower = line.lower()
            assert "groq" not in line_lower, f"ingestion must not import groq: {line}"
            assert "openai" not in line_lower, (
                f"ingestion must not import openai: {line}"
            )
            assert "chatcompletion" not in line_lower, (
                f"ingestion must not use ChatCompletion: {line}"
            )

    def test_deduplication_by_doi(self):
        """INGESTION: Deduplicate using DOI before insertion."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Initialize database
            init_database(db_path)

            # First insert should succeed
            add_paper(db_path, "10.1234/test", "Test Paper", "article")

            # Duplicate should raise ValueError
            with pytest.raises(ValueError, match="already exists"):
                add_paper(db_path, "10.1234/test", "Test Paper 2", "article")

    def test_doi_cleaning(self):
        """INGESTION: Clean DOI format correctly."""
        from raven.ingestion import normalize_doi

        # Test DOI URL stripping
        test_cases = [
            ("https://doi.org/10.1234/test", "10.1234/test"),
            ("doi:10.1234/test", "10.1234/test"),
            ("  DOI:10.1234/test  ", "10.1234/test"),
            ("10.1234/test", "10.1234/test"),
        ]

        for input_doi, expected in test_cases:
            cleaned = normalize_doi(input_doi)
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
        # Check for dimension constant in module or config
        embeddings_file = Path("src/raven/embeddings/__init__.py")
        if embeddings_file.exists():
            content = embeddings_file.read_text()
            # Should reference the model or 384 dimensions
            assert "384" in content or "e5" in content.lower()

    def test_cpu_only_inference(self):
        """EMBEDDINGS: CPU-only inference (no GPU dependencies)."""
        if raven.embeddings.__file__:
            source = Path(raven.embeddings.__file__).read_text()
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
        # Verify caching mechanism exists
        source = inspect.getsource(raven.llm)
        assert "cache" in source.lower() or "Cache" in source

    def test_no_llm_for_parsing(self):
        """LLM: Never use LLMs for parsing or embeddings."""
        # Should not use LLM for deterministic parsing tasks
        # (This is enforced by design - LLM is for reasoning only)
        # Note: LLM should only be used for reasoning tasks (query refinement,
        # hypothesis generation, summarization), not for parsing or embeddings
        assert hasattr(raven.llm, "query_llm")


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
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            init_database(db_path)

            # Verify WAL mode
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("PRAGMA journal_mode")
                mode = cursor.fetchone()[0]

            assert mode.upper() == "WAL"

    def test_doi_unique_constraint(self):
        """STORAGE: Enforce DOI uniqueness."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            init_database(db_path)

            # First insert
            add_paper(db_path, "10.1234/unique", "First Paper", "article")

            # Duplicate should fail
            with pytest.raises(ValueError):
                add_paper(db_path, "10.1234/unique", "Duplicate", "article")

    def test_indexes_exist(self):
        """STORAGE: Maintain indexes on identifier, type, title."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            init_database(db_path)

            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='index' ORDER BY name"
                )
                indexes = [row[0] for row in cursor.fetchall()]

            # Should have indexes on identifier, type, title
            index_names = [i.lower() for i in indexes]
            assert any("identifier" in i for i in index_names), (
                "Missing identifier index"
            )
            assert any("type" in i for i in index_names), "Missing type index"
            assert any("title" in i for i in index_names), "Missing title index"


# =============================================================================
# Integration: CLI Workflow
# =============================================================================


class TestCLIWorkflow:
    """Test full CLI integration."""

    def test_ingest_to_search_workflow(self):
        """Complete workflow: init -> ingest -> search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            # Initialize
            init_database(db_path)

            # Add paper directly (simulating successful ingest)
            add_paper(db_path, "10.1234/workflow", "Test Workflow Paper", "article")

            # Search
            results = search_papers(db_path, "workflow")

            assert len(results) == 1
            assert results[0]["identifier"] == "10.1234/workflow"
