"""Configuration module for Raven - loads environment variables from .env file."""

from pathlib import Path

# Import paths module at top level for backward compat _config
import raven.paths  # noqa: E402
from raven.paths import (
    find_env_file,
    get_data_dir,
    load_config,
    lookup,
    parse_env_file,
    reset_config,
)

# Default values
DEFAULT_OPENALEX_API_URL = "https://api.openalex.org"
DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"

__all__ = [
    "get_data_dir",
    "load_config",
    "reset_config",
    "find_env_file",
    "parse_env_file",
    "get_groq_api_key",
    "get_groq_model",
    "get_openalex_api_key",
    "get_openalex_api_url",
    # Backward compatibility aliases
    "_get_data_dir",
    "_load_config",
    "_reset_config",
    "_lookup",
    "_find_env_file",
    "_parse_env_file",
    "_config",
]

# Type alias for config dict
ConfigDict = dict[str, str]

# Backward compatibility: _config references paths._config
_config: ConfigDict = raven.paths._config  # type: ignore[assignment]


def get_groq_api_key() -> str:
    """Get GROQ_API_KEY from environment."""
    api_key = lookup("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Please add it to your .env file.\n"
            "Get your API key at: https://console.groq.com/"
        )
    return api_key


def get_groq_model() -> str:
    """Get GROQ_MODEL from environment."""
    return lookup("GROQ_MODEL") or DEFAULT_GROQ_MODEL


def get_openalex_api_key() -> str:
    """Get OPENALEX_API_KEY from environment."""
    api_key = lookup("OPENALEX_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENALEX_API_KEY is not set. Please add it to your .env file.\n"
            "Get your API key at: https://openalex.org/"
        )
    return api_key


def get_openalex_api_url() -> str:
    """Get OPENALEX_API_URL from environment."""
    return lookup("OPENALEX_API_URL") or DEFAULT_OPENALEX_API_URL


# Backward compatibility aliases (with underscore prefix)
_get_data_dir = get_data_dir
_load_config_orig = load_config
_reset_config_orig = reset_config
_lookup_orig = lookup
_find_env_file = find_env_file
_parse_env_file = parse_env_file


def _reset_config() -> None:
    """Reset both config caches for testing."""
    _reset_config_orig()
    global _config
    _config = {}


def _load_config(env_path: str | Path | None = None) -> ConfigDict:
    """Load configuration from .env file (backward compat wrapper)."""
    global _config
    _config = {}
    _reset_config_orig()
    return _load_config_orig(env_path)


def _lookup(key: str, default: str | None = None) -> str | None:
    """Look up a config value (backward compat wrapper)."""
    return _lookup_orig(key, default)


def __getattr__(name: str) -> object:
    """Lazy loading for module-level attributes."""
    if name == "get_data_dir":
        return get_data_dir
    if name == "load_config":
        return load_config
    if name == "lookup":
        return lookup
    # Backward compatibility
    if name == "_get_data_dir":
        return _get_data_dir
    if name == "_load_config":
        return _load_config
    if name == "_reset_config":
        return _reset_config
    if name == "_lookup":
        return _lookup
    if name == "_find_env_file":
        return _find_env_file
    if name == "_parse_env_file":
        return _parse_env_file
    if name == "_config":
        return _config
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
