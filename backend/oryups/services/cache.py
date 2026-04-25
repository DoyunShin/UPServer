import copy
import threading
import time
from typing import Optional

from oryups.config import get_config, get_storage
from oryups.filesystem import Metadata
from oryups.utils.expiry import is_expired

_cache: dict[str, dict] = {}
_tombstones: dict[str, float] = {}
_cache_lock: threading.Lock = threading.Lock()


def _tombstone_ttl() -> int:
    """How long an invalidated fileid blocks new cache stores.

    Matches ``host.cachetime`` so any stale read whose storage call
    started before the corresponding ``invalidate`` cannot survive past
    the moment its cache entry would have naturally expired.
    """
    return int(get_config()["host"].get("cachetime", 600))


def _prune_tombstones_locked(now: float) -> None:
    """Drop expired tombstone entries. Caller must hold ``_cache_lock``."""
    expired = [fileid for fileid, deadline in _tombstones.items() if deadline <= now]
    for fileid in expired:
        _tombstones.pop(fileid, None)


def _redacted_copy(metadata: Metadata) -> Metadata:
    """Return a shallow copy of metadata with the owner key cleared.

    Cache entries must never carry the owner key. Storage layers (especially
    the gdrive queue) hold the same Metadata instance and rely on its
    ``delete`` field surviving until the upload is durably written, so we
    must never mutate the caller's object.
    """
    redacted = copy.copy(metadata)
    redacted.delete = ""
    return redacted


def store_cache(metadata: Metadata) -> None:
    """Cache a redacted copy of metadata keyed by file id.

    Skips the store entirely when the fileid is currently tombstoned —
    that means a concurrent ``invalidate`` (typically a DELETE) ran
    between the storage read and this commit, and accepting the entry
    would poison the cache with metadata for an already-removed file.
    """
    now = time.time()
    with _cache_lock:
        _prune_tombstones_locked(now)
        if metadata.id in _tombstones:
            return
        _cache[metadata.id] = {
            "time": int(now),
            "metadata": _redacted_copy(metadata),
        }


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
    """Evict all expired cache entries and tombstones."""
    cachetime = get_config()["host"]["cachetime"]
    now = time.time()
    with _cache_lock:
        for fileid in list(_cache.keys()):
            entry = _cache.get(fileid)
            if entry is not None and entry["time"] + cachetime < now:
                _cache.pop(fileid, None)
        _prune_tombstones_locked(now)


def invalidate(fileid: str) -> None:
    """Drop a file's cached metadata and tombstone the fileid.

    The tombstone blocks concurrent readers (whose storage I/O began
    before this call) from later writing a stale cache entry. The
    tombstone TTL matches ``host.cachetime`` so any in-flight read is
    safely contained.
    """
    now = time.time()
    deadline = now + _tombstone_ttl()
    with _cache_lock:
        _prune_tombstones_locked(now)
        _cache.pop(fileid, None)
        _tombstones[fileid] = deadline


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
        store_cache(metadata)
        metadata = get_cache(fileid, filename) or _redacted_copy(metadata)

    if is_expired(metadata, get_config().get("delete", {})):
        with _cache_lock:
            _cache.pop(fileid, None)
        raise FileNotFoundError(f"{fileid}/{filename} expired")
    return metadata
