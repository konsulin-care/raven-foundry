"""Pytest configuration and fixtures for Raven Foundry tests."""

import os
from pathlib import Path
from typing import Generator

import pytest

import raven.config


@pytest.fixture(autouse=True)
def reset_config_cache() -> Generator[None, None, None]:
    """Reset config cache before each test to ensure test isolation.

    This fixture runs automatically before each test to clear the global config cache.
    Without this, config loaded in one test can leak into another.
    """
    # Clear the global config cache
    raven.config._config = {}
    yield
    # Clean up after test
    raven.config._config = {}


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
    raven.config._config = {}


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
    # Ensure no .env file is found (override the search path)
    monkeypatch.setattr(raven.config, "_find_env_file", lambda: None)

    # Set test values in environment
    original_env = os.environ.copy()
    os.environ["OPENALEX_API_KEY"] = "test-key"
    os.environ["GROQ_API_KEY"] = "test-key"
    os.environ["OPENALEX_API_URL"] = "https://api.openalex.org"

    yield

    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)
