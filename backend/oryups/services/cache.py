import threading
import time
from typing import Optional

from oryups.config import get_config, get_storage
from oryups.filesystem import Metadata
from oryups.utils.expiry import is_expired

_cache: dict[str, dict] = {}
_cache_lock: threading.Lock = threading.Lock()


def store_cache(metadata: Metadata) -> None:
    """Cache metadata by file id with a timestamp."""
    with _cache_lock:
        _cache[metadata.id] = {"time": int(time.time()), "metadata": metadata}


def get_cache(fileid: str, filename: str) -> Optional[Metadata]:
    """Return cached metadata if present and not expired.

    Args:
        fileid(str): File id
        filename(str): Expected filename (must match cached metadata)

    Return:
        metadata(Metadata | None): Cached metadata or None on miss/expiry.
    """
    cachetime = get_config()["host"]["cachetime"]
    now = int(time.time())
    with _cache_lock:
        entry = _cache.get(fileid)
        if entry is None:
            return None
        if entry["metadata"].name != filename:
            return None
        if entry["time"] + cachetime <= now:
            _cache.pop(fileid, None)
            return None
        return entry["metadata"]


def clear_cache() -> None:
    """Evict all expired cache entries."""
    cachetime = get_config()["host"]["cachetime"]
    now = int(time.time())
    with _cache_lock:
        for fileid in list(_cache.keys()):
            entry = _cache.get(fileid)
            if entry is not None and entry["time"] + cachetime < now:
                _cache.pop(fileid, None)


def invalidate(fileid: str) -> None:
    """Drop a single file's cached metadata, if any."""
    with _cache_lock:
        _cache.pop(fileid, None)


def load_metadata(fileid: str, filename: str) -> Metadata:
    """Load metadata for (fileid, filename), using cache when possible.

    Enforces retention: if ``config["delete"]`` marks the file as expired,
    the cache entry is evicted and ``FileNotFoundError`` is raised so the
    router returns 404.

    Args:
        fileid(str): File id
        filename(str): Filename

    Return:
        metadata(Metadata): Metadata object.
    """
    metadata = get_cache(fileid, filename)
    if metadata is None:
        metadata = get_storage().load_metadata(fileid, filename)
        metadata.delete = ""
        store_cache(metadata)

    if is_expired(metadata, get_config().get("delete", {})):
        with _cache_lock:
            _cache.pop(fileid, None)
        raise FileNotFoundError(f"{fileid}/{filename} expired")
    return metadata
