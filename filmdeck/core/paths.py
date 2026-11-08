"""Where FilmDeck keeps its files (XDG base directories).

``FILMDECK_HOME`` moves everything under one directory; the tests use it so
they never touch the real configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

DIR_NAME = "filmdeck"


def _base(env: str, fallback: str) -> Path:
    value = os.environ.get(env)
    if value and os.path.isabs(value):
        return Path(value)
    return Path.home() / fallback


def _home_override() -> Path | None:
    value = os.environ.get("FILMDECK_HOME")
    return Path(value) if value else None


def config_dir() -> Path:
    override = _home_override()
    return override / "config" if override else _base("XDG_CONFIG_HOME", ".config") / DIR_NAME


def data_dir() -> Path:
    override = _home_override()
    return override / "data" if override else _base("XDG_DATA_HOME", ".local/share") / DIR_NAME


def settings_file() -> Path:
    return config_dir() / "settings.json"


def log_dir() -> Path:
    return data_dir() / "logs"


def driver_root_dir() -> Path:
    """Parent of the managed driver installs (``<tag>/`` and ``current``)."""
    return data_dir() / "driver"


def default_scan_dir() -> Path:
    return Path.home() / "Pictures" / "Filmscans"
