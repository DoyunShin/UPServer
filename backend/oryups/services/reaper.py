import asyncio
from pathlib import Path
from typing import Optional

from fastapi.concurrency import run_in_threadpool

from oryups.config import get_config, get_storage
from oryups.filesystem import Metadata, gdrive as GDriveStorage, local as LocalStorage
from oryups.services import cache
from oryups.utils.expiry import is_expired


async def run_reaper(stop_event: asyncio.Event) -> None:
    """Run the periodic reaper loop until ``stop_event`` is set.

    Args:
        stop_event(asyncio.Event): Set by the lifespan to request shutdown.
    """
    while not stop_event.is_set():
        try:
            await run_in_threadpool(reap_once)
        except Exception as exc:
            print(f"[reaper] exception: {exc!r}")

        interval = _get_reaper_interval()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=max(60, interval))
        except asyncio.TimeoutError:
            continue


def _get_reaper_interval() -> int:
    """Read ``delete.reaper_interval`` from config, defaulting to 3600."""
    try:
        return int(get_config().get("delete", {}).get("reaper_interval", 3600))
    except (TypeError, ValueError):
        return 3600


def reap_once() -> int:
    """Scan storage once, deleting every expired file.

    Return:
        removed(int): Number of files permanently removed.
    """
    cfg = get_config()
    delete_rule = cfg.get("delete", {})
    if not (delete_rule.get("enabled") and delete_rule.get("permanently")):
        return 0

    storage = get_storage()
    if isinstance(storage, LocalStorage):
        return _reap_local(storage, delete_rule)
    if isinstance(storage, GDriveStorage):
        return _reap_gdrive(storage, delete_rule)
    return 0


def _reap_local(storage: LocalStorage, delete_rule: dict) -> int:
    removed = 0
    try:
        entries = list(storage.root.iterdir())
    except FileNotFoundError:
        return 0

    for folder in entries:
        if not folder.is_dir() or folder.name == "delete":
            continue
        metadata_path = _find_metadata_path(folder)
        if metadata_path is None:
            continue
        try:
            metadata = Metadata()
            metadata.load(dataPath=metadata_path)
        except Exception as exc:
            print(f"[reaper] failed to load {metadata_path}: {exc!r}")
            continue
        if not is_expired(metadata, delete_rule):
            continue
        try:
            if storage._remove_permanent(metadata.id, metadata.name):
                cache.invalidate(metadata.id)
                removed += 1
        except Exception as exc:
            print(f"[reaper] failed to remove {metadata.id}/{metadata.name}: {exc!r}")
    return removed


def _find_metadata_path(folder: Path) -> Optional[Path]:
    """Return the first ``*.metadata`` file in ``folder`` or None."""
    try:
        for entry in folder.iterdir():
            if entry.is_file() and entry.name.endswith(".metadata"):
                return entry
    except FileNotFoundError:
        return None
    return None


def _reap_gdrive(storage: GDriveStorage, delete_rule: dict) -> int:
    removed = 0
    try:
        root_list = storage.get_list(dir=storage.root, mimeType="application/vnd.google-apps.folder")
    except Exception as exc:
        print(f"[reaper] gdrive list failed: {exc!r}")
        return 0

    for fileid, folderid in root_list.items():
        if fileid == "delete":
            continue
        try:
            files = storage.get_list(dir=folderid)
        except Exception as exc:
            print(f"[reaper] gdrive list {fileid} failed: {exc!r}")
            continue
        filename = next((n for n in files if not n.endswith(".metadata")), None)
        if not filename:
            continue
        try:
            metadata = storage.load_metadata(fileid, filename)
        except Exception as exc:
            print(f"[reaper] gdrive metadata {fileid} failed: {exc!r}")
            continue
        if not is_expired(metadata, delete_rule):
            continue
        try:
            if storage.remove(fileid, filename, metadata.delete, force=True, permanently=True):
                cache.invalidate(fileid)
                removed += 1
        except Exception as exc:
            print(f"[reaper] gdrive remove {fileid} failed: {exc!r}")
    return removed
