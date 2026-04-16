"""Configuration module for Raven - loads environment variables from .env file."""

from pathlib import Path

from raven.paths import find_env_file, get_data_dir, load_config

# Default values
DEFAULT_OPENALEX_API_URL = "https://api.openalex.org"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

__all__ = [
    "get_data_dir",
    "load_config",
    "find_env_file",
    "get_groq_api_key",
    "get_groq_model",
    "get_openalex_api_key",
    "get_openalex_api_url",
]


def get_groq_api_key() -> str:
    """Get GROQ_API_KEY from environment."""
    from raven.paths import lookup

    api_key = lookup("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Please add it to your .env file.\n"
            "Get your API key at: https://console.groq.com/"
        )
    return api_key


def get_groq_model() -> str:
    """Get GROQ_MODEL from environment."""
    from raven.paths import lookup

    return lookup("GROQ_MODEL") or DEFAULT_GROQ_MODEL


def get_openalex_api_key() -> str:
    """Get OPENALEX_API_KEY from environment."""
    from raven.paths import lookup

    api_key = lookup("OPENALEX_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENALEX_API_KEY is not set. Please add it to your .env file.\n"
            "Get your API key at: https://openalex.org/"
        )
    return api_key


def get_openalex_api_url() -> str:
    """Get OPENALEX_API_URL from environment."""
    from raven.paths import lookup

    return lookup("OPENALEX_API_URL") or DEFAULT_OPENALEX_API_URL
