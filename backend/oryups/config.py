import os
from json import loads
from pathlib import Path
from typing import Optional

from oryups import filesystem

PKG_DIR: Path = Path(__file__).resolve().parent
BASE_DIR: Path = PKG_DIR.parent
STATIC_DIR: Path = PKG_DIR / "static"
ASSETS_DIR: Path = STATIC_DIR / "assets"

_config: dict = {}
_config_path: Optional[Path] = None
_storage: Optional[filesystem.storage] = None


def _resolve_config_path(path: Optional[Path]) -> Path:
    """Pick the config path, honoring explicit arg > env var > default."""
    if path is not None:
        return path
    env_path = os.environ.get("UPSERVER_CONFIG")
    if env_path:
        return Path(env_path)
    return BASE_DIR / "config.json"


def load_config(path: Optional[Path] = None) -> dict:
    """Load UPServer configuration and initialize the storage backend.

    Idempotent when called without an explicit ``path``: if the config has
    already been loaded (for example by the ``ups`` CLI before uvicorn
    started), a subsequent call from the app lifespan returns the cached
    dict instead of re-reading the file. Pass an explicit ``path`` to force
    a reload against a different file.

    Args:
        path(pathlib.Path, optional): Explicit config.json path. If not given,
            falls back to the ``UPSERVER_CONFIG`` environment variable and
            then to ``backend/config.json``.

    Return:
        config(dict): Parsed configuration dict.
    """
    global _config, _config_path, _storage

    if path is None and _config:
        return _config

    _config_path = _resolve_config_path(path)
    if not _config_path.exists():
        raise FileNotFoundError(f"Config file not found: {_config_path}")

    _config = loads(_config_path.read_text())
    storage_name = _config["storage"]
    if storage_name not in filesystem.storageTypes:
        raise ValueError(f"Invalid storage type: {storage_name}")

    _storage = getattr(filesystem, storage_name)(_config, _config_path)
    return _config


def get_config() -> dict:
    """Return the loaded config dict. Raises if load_config was not called."""
    if not _config:
        raise RuntimeError("Config has not been loaded yet")
    return _config


def get_storage() -> filesystem.storage:
    """Return the initialized storage backend."""
    if _storage is None:
        raise RuntimeError("Storage has not been initialized yet")
    return _storage


def get_config_path() -> Path:
    """Return the path config was loaded from."""
    if _config_path is None:
        raise RuntimeError("Config has not been loaded yet")
    return _config_path
