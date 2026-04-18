"""Pytest configuration and fixtures for Raven Foundry tests."""

import os
import sqlite3
from pathlib import Path
from typing import Generator

import pytest

import raven.paths


@pytest.fixture(autouse=True)
def reset_config_cache() -> Generator[None, None, None]:
    """Reset config cache before each test to ensure test isolation.

    This fixture runs automatically before each test to clear the global config cache
    and remove test-related environment variables. Without this, config loaded in
    one test can leak into another.
    """
    # Store and remove test-related env vars
    test_env_keys = [
        "OPENALEX_API_KEY",
        "OPENALEX_API_URL",
        "GROQ_API_KEY",
        "GROQ_MODEL",
        "RAVEN_DATA_DIR",
    ]
    original_vals = {k: os.environ.get(k) for k in test_env_keys}
    for k in test_env_keys:
        os.environ.pop(k, None)

    # Clear the config cache in paths module only
    raven.paths._config = {}

    yield

    # Clean up after test
    raven.paths._config = {}
    # Restore original env vars
    for k, v in original_vals.items():
        if v is not None:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


@pytest.fixture
def mock_env(tmp_path: Path) -> Generator[dict, None, None]:
    """Create a temporary .env file for tests that need config.

    Usage:
        def test_something(mock_env):
            mock_env["OPENALEX_API_KEY"] = "test-key"
            # test code here
    """
    env_file = tmp_path / ".env"
    env_data = {}

    # Create a minimal env file builder
    def set_key(key: str, value: str) -> None:
        env_data[key] = value
        env_file.write_text("\n".join(f"{k}={v}" for k, v in env_data.items()))

    # Set minimal required keys for most tests
    set_key("OPENALEX_API_KEY", "test-key")
    set_key("GROQ_API_KEY", "test-key")

    yield env_data

    # Cleanup
    raven.paths._config = {}


@pytest.fixture
def mock_api_keys(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """Set environment variables for API keys.

    This is more robust than patching because it works regardless of
    where functions are imported.

    Usage:
        def test_something(mock_api_keys):
            # raven.config functions will read from os.environ
            pass
    """
    # Ensure no .env file is found
    monkeypatch.setattr(raven.paths, "find_env_file", lambda env_path=None: None)

    # Set test values in environment
    original_env = os.environ.copy()
    os.environ["OPENALEX_API_KEY"] = "test-key"
    os.environ["GROQ_API_KEY"] = "test-key"
    os.environ["OPENALEX_API_URL"] = "https://api.openalex.org"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


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
