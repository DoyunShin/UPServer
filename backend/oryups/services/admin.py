import logging
from pathlib import Path
from typing import Optional

from oryups.config import get_config, get_storage
from oryups.filesystem import Metadata, gdrive as GDriveStorage, local as LocalStorage
from oryups.utils.expiry import is_expired


logger = logging.getLogger("oryups.admin")


def list_all_files() -> dict[str, list[dict]]:
    """List every file currently held by the storage backend.

    Splits the result into two buckets keyed by retention status:

    * ``active`` -- files still within their retention window.
    * ``expired`` -- files whose retention window has passed but that still
      exist on disk (or in the gdrive folder tree). The public download path
      already 404s for these via :func:`oryups.services.cache.load_metadata`.

    Soft-deleted entries (``delete/`` folder) and tombstones
    (``.tombstones/``) are intentionally excluded -- the goal is to surface
    "still here but 404", not the deletion history.

    Return:
        result(dict): ``{"active": [item, ...], "expired": [item, ...]}``
        where each ``item`` is the dict produced by :func:`classify_metadata`.
    """
    storage = get_storage()
    delete_rule = get_config().get("delete", {})

    if isinstance(storage, LocalStorage):
        entries = list_local_entries(storage)
    elif isinstance(storage, GDriveStorage):
        entries = list_gdrive_entries(storage)
    else:
        raise RuntimeError(
            f"Unsupported storage backend: {type(storage).__name__}"
        )

    active: list[dict] = []
    expired: list[dict] = []
    for metadata in entries:
        item = classify_metadata(metadata, delete_rule)
        if item["expired"]:
            expired.append(item)
        else:
            active.append(item)
    return {"active": active, "expired": expired}


def list_local_entries(storage: LocalStorage) -> list[Metadata]:
    """Iterate the local storage root and yield Metadata for every file folder.

    Skips the ``delete`` soft-delete bucket and any name that begins with a
    dot (covers ``.tombstones``). Folders without a ``*.metadata`` sidecar
    are treated as not-yet-finalized uploads and ignored.

    Args:
        storage(LocalStorage): The configured local storage backend.

    Return:
        entries(list[Metadata]): Loaded metadata, one per file folder.
    """
    try:
        folders = list(storage.root.iterdir())
    except FileNotFoundError:
        # The storage root has not been materialized yet (no uploads have
        # happened on this fresh deployment). That's a legitimate "empty"
        # state, not a failure, so we keep the bucket empty rather than
        # surfacing 500 to the operator.
        return []

    entries: list[Metadata] = []
    for folder in folders:
        if not folder.is_dir():
            continue
        if folder.name == "delete" or folder.name.startswith("."):
            continue
        metadata_path = _find_metadata_path(folder)
        if metadata_path is None:
            continue
        try:
            metadata = Metadata()
            metadata.load(dataPath=metadata_path)
        except Exception as exc:
            logger.warning("Failed to load %s: %r", metadata_path, exc)
            continue
        entries.append(metadata)
    return entries


def list_gdrive_entries(storage: GDriveStorage) -> list[Metadata]:
    """Iterate the gdrive storage root and yield Metadata for every file folder.

    Mirrors :func:`oryups.services.reaper._reap_gdrive`: list root subfolders,
    list each subfolder's contents, locate the non-``.metadata`` filename,
    then load metadata.

    Args:
        storage(GDriveStorage): The configured gdrive storage backend.

    Return:
        entries(list[Metadata]): Loaded metadata, one per file folder.
    """
    root_list = storage.get_list(
        dir=storage.root,
        mimeType="application/vnd.google-apps.folder",
    )

    entries: list[Metadata] = []
    for fileid, folderid in root_list.items():
        if fileid == "delete":
            continue
        try:
            files = storage.get_list(dir=folderid)
        except Exception as exc:
            logger.warning("gdrive list %s failed: %r", fileid, exc)
            continue
        filename = next((n for n in files if not n.endswith(".metadata")), None)
        if not filename:
            continue
        try:
            metadata = storage.load_metadata(fileid, filename)
        except Exception as exc:
            logger.warning("gdrive metadata %s failed: %r", fileid, exc)
            continue
        entries.append(metadata)
    return entries


def classify_metadata(metadata: Metadata, delete_rule: dict) -> dict:
    """Convert a Metadata object to the API dict shape with retention status.

    Args:
        metadata(Metadata): Loaded metadata object.
        delete_rule(dict): The ``config["delete"]`` block.

    Return:
        item(dict): Plain dict with id, name, mimeType, size, created_at,
        delete_after, expires_at, expired. The owner key is never included.
    """
    base = metadata.to_dict(private=False)
    delete_after = float(getattr(metadata, "delete_after", -1) or -1)
    created_at = float(getattr(metadata, "created_at", 0) or 0)
    expires_at: Optional[float]
    if delete_after > 0:
        expires_at = created_at + delete_after
    else:
        expires_at = None
    base["expires_at"] = expires_at
    base["expired"] = is_expired(metadata, delete_rule)
    return base


def _find_metadata_path(folder: Path) -> Optional[Path]:
    """Return the first ``*.metadata`` file in ``folder`` or None."""
    try:
        for entry in folder.iterdir():
            if entry.is_file() and entry.name.endswith(".metadata"):
                return entry
    except FileNotFoundError:
        return None
    return None
