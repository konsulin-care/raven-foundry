"""Path and environment configuration for Raven.

Handles data directory resolution and .env file discovery.
"""

import os
import platform
from pathlib import Path
from typing import Optional

# Global config cache
_config: dict[str, str] = {}


def reset_config() -> None:
    """Reset the config cache. Used for testing."""
    global _config
    _config = {}


def get_data_dir() -> Path:
    """Get data directory, cross-platform compatible.

    Returns the appropriate data directory based on OS:
    - Windows: %APPDATA%/raven
    - macOS/Linux: $XDG_DATA_HOME/raven if set, otherwise ~/.config/raven

    Override with RAVEN_DATA_DIR environment variable.
    """
    # Allow override via environment variable
    data_dir = os.environ.get("RAVEN_DATA_DIR")
    if data_dir:
        return Path(data_dir)

    system = platform.system()
    home = Path.home()

    if system == "Windows":
        # Windows: %APPDATA%
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "raven"
        return home / "AppData" / "Roaming" / "raven"
    else:
        # macOS/Linux: XDG_DATA_HOME if set, otherwise ~/.config
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            return Path(xdg_data) / "raven"
        return home / ".config" / "raven"


def find_env_file(env_path: str | Path | None = None) -> Optional[Path]:
    """Find .env file.

    Args:
        env_path: Explicit path to .env file. If provided and exists, use it directly.
                If None, falls back to default logic:
                - Check cwd/.env first
                - Fall back to data_dir/.env

    Returns:
        Path to .env file if found, None otherwise.
    """
    # 1. User-provided explicit path
    if env_path is not None:
        path_obj = Path(env_path) if isinstance(env_path, str) else env_path
        if path_obj.exists() and path_obj.is_file():
            return path_obj
        return None

    # 2. Default: cwd/.env
    cwd_env = Path.cwd() / ".env"
    if cwd_env.exists():
        return cwd_env

    # 3. Default: data_dir/.env
    data_dir = get_data_dir()
    data_env = data_dir / ".env"
    if data_env.exists():
        return data_env

    return None


def parse_env_file(env_path: Path) -> dict[str, str]:
    """Parse .env file and return dict of key-value pairs."""
    config: dict[str, str] = {}

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


def load_config(env_path: str | Path | None = None) -> dict[str, str]:
    """Load configuration from .env file.

    Args:
        env_path: Explicit path to .env file. If provided and exists, use it.
                If None, uses default logic (cwd/.env -> data_dir/.env).

    Note:
        Loaded values are propagated to os.environ to ensure consistency
        across the application (e.g., get_data_dir() reads RAVEN_DATA_DIR).
        Results are cached after first load.
    """
    global _config
    if _config:  # Already loaded - return cached
        return _config

    env_path = find_env_file(env_path)

    if env_path:
        _config = parse_env_file(env_path)
    else:
        _config = {}

    # Propagate loaded config to os.environ for consistency
    for key, value in _config.items():
        os.environ[key] = value

    return _config


def lookup(key: str, default: str | None = None) -> str | None:
    """Look up a config value from cache or environment.

    Args:
        key: Configuration key.
        default: Default value if not found.

    Returns:
        Config value or default.
    """
    config = load_config()
    return config.get(key) or os.environ.get(key) or default
