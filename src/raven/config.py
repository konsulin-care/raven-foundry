"""Configuration module for Raven - loads environment variables from .env file."""

from pathlib import Path
from typing import Optional

# Default values
DEFAULT_OPENALEX_API_URL = "https://api.openalex.org"

# Global config cache
_config: dict = {}


def _find_env_file() -> Optional[Path]:
    """Find .env file by searching upward from current working directory."""
    cwd = Path.cwd()

    # Check current directory and parent directories
    for path in [cwd, cwd.parent, cwd.parent.parent]:
        env_path = path / ".env"
        if env_path.exists():
            return env_path

    return None


def _parse_env_file(env_path: Path) -> dict:
    """Parse .env file and return dict of key-value pairs."""
    config = {}

    if not env_path.exists():
        return config

    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue

            # Parse key=value
            if "=" in line:
                key, value = line.split("=", 1)
                config[key.strip()] = value.strip()

    return config


def _load_config() -> dict:
    """Load configuration from .env file."""
    global _config

    if _config:
        return _config

    env_path = _find_env_file()

    if env_path:
        _config = _parse_env_file(env_path)
    else:
        _config = {}

    return _config


def get_groq_api_key() -> str:
    """Get GROQ_API_KEY from environment.

    Returns:
        The API key string.

    Raises:
        ValueError: If GROQ_API_KEY is not set in .env file.
    """
    config = _load_config()

    api_key = config.get("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Please add it to your .env file.\n"
            "Get your API key at: https://console.groq.com/"
        )

    return api_key


def get_openalex_api_key() -> str:
    """Get OPENALEX_API_KEY from environment.

    Returns:
        The API key string.

    Raises:
        ValueError: If OPENALEX_API_KEY is not set in .env file.
    """
    config = _load_config()

    api_key = config.get("OPENALEX_API_KEY", "")
    if not api_key:
        raise ValueError(
            "OPENALEX_API_KEY is not set. Please add it to your .env file.\n"
            "Get your API key at: https://openalex.org/"
        )

    return api_key


def get_openalex_api_url() -> str:
    """Get OPENALEX_API_URL from environment.

    Returns:
        The API URL string, defaults to https://api.openalex.org if not set.
    """
    config = _load_config()

    return config.get("OPENALEX_API_URL", DEFAULT_OPENALEX_API_URL)
