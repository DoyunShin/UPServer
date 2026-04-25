import io
import secrets
from typing import AsyncIterator
from urllib.parse import urlparse

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import (
    FileResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)

from oryups.config import STATIC_DIR, get_config, get_storage
from oryups.response import make_response
from oryups.services import cache
from oryups.utils.upload import buffer_request_body
from oryups.utils.validation import (
    validate_fileid,
    validate_filename_for_read,
    validate_filename_for_write,
)

DEFAULT_MAX_UPLOAD_SIZE: int = 1 << 30
GDRIVE_STREAM_CHUNK: int = 8 * 1024 * 1024

# Mime types that browsers can render same-origin and that have been used as
# reflected-XSS vectors when served from user uploads. We always downgrade
# these on the download path.
_DANGEROUS_DOWNLOAD_MIMES: frozenset[str] = frozenset({
    "text/html",
    "application/xhtml+xml",
    "image/svg+xml",
    "application/javascript",
    "text/javascript",
    "application/x-javascript",
    "application/xml",
    "text/xml",
})

_SAFE_DOWNLOAD_MIME: str = "application/octet-stream"


def _content_disposition(filename: str) -> str:
    r"""Build a safe ``Content-Disposition: attachment`` header value.

    Always emits both the legacy quoted ``filename="..."`` and the
    RFC 5987 ``filename*=UTF-8''...`` so non-ASCII names render in modern
    browsers. The legacy form is escaped against header injection by
    backslash-escaping ``\`` and ``"`` and stripping CR/LF.
    """
    from urllib.parse import quote

    legacy = filename.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "")
    encoded = quote(filename, safe="")
    return f'attachment; filename="{legacy}"; filename*=UTF-8\'\'{encoded}'


def _safe_download_mime(raw: str | None) -> str:
    """Return a safe Content-Type for serving uploaded bytes.

    Strips any parameters (charset, boundary) before comparing to the
    deny-list, then falls back to ``application/octet-stream`` when the
    mime is dangerous, missing, or malformed.
    """
    if not raw:
        return _SAFE_DOWNLOAD_MIME
    base = raw.split(";", 1)[0].strip().lower()
    if not base or base in _DANGEROUS_DOWNLOAD_MIMES:
        return _SAFE_DOWNLOAD_MIME
    return base


router = APIRouter(tags=["Files"])


def _is_curl_ua(request: Request) -> bool:
    """Detect whether the request looks like a curl client."""
    return "curl" in request.headers.get("user-agent", "")


def _resolve_base_url(request: Request, config: dict) -> str:
    """Pick the public base URL for generated share links.

    Prefers ``config["host"]["domain"]`` so attackers cannot poison the URL
    via a forged ``Host`` header; falls back to ``request.base_url`` when no
    trustworthy domain is configured.
    """
    domain = (config["host"].get("domain") or "").strip()
    if domain and domain.startswith(("http://", "https://")):
        return domain if domain.endswith("/") else domain + "/"
    return str(request.base_url)


async def _stream_gdrive(storage, gfile_id: str) -> AsyncIterator[bytes]:
    """Yield gdrive file bytes chunk-by-chunk without buffering the full payload."""
    from googleapiclient.http import MediaIoBaseDownload

    request_obj = storage.service.files().get_media(fileId=gfile_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request_obj, chunksize=GDRIVE_STREAM_CHUNK)

    def _pull_chunk() -> tuple[bytes, bool]:
        _, finished_now = downloader.next_chunk()
        chunk = buffer.getvalue()
        buffer.seek(0)
        buffer.truncate()
        return chunk, finished_now

    finished = False
    while not finished:
        data, finished = await run_in_threadpool(_pull_chunk)
        if data:
            yield data


async def _load_metadata(fileid: str, filename: str):
    """Load metadata off the event loop (storage backends may do network I/O)."""
    return await run_in_threadpool(cache.load_metadata, fileid, filename)


async def _download_response(fileid: str, filename: str) -> Response:
    """Build the file download response using the configured storage backend."""
    config = get_config()
    validate_fileid(fileid, config["folderidlength"])
    validate_filename_for_read(filename)

    storage = get_storage()

    try:
        if storage.cache and storage.is_cached(fileid, filename):
            cached_path = storage.get_cached(fileid, filename)
            metadata = await _load_metadata(fileid, filename)
            safe_mime = _safe_download_mime(metadata.mimeType)
            return FileResponse(
                cached_path,
                media_type=safe_mime,
                filename=metadata.name,
                content_disposition_type="attachment",
            )

        if config["host"]["cdn"]["enabled"]:
            cdn_url = config["host"]["cdn"]["url"].rstrip("/")
            return RedirectResponse(f"{cdn_url}/{fileid}/{filename}")

        metadata = await _load_metadata(fileid, filename)
        storage_name = config["storage"]
        safe_mime = _safe_download_mime(metadata.mimeType)

        if storage_name == "local":
            file_path = storage.root / fileid / filename
            if not file_path.is_file():
                raise FileNotFoundError(f"{fileid}/{filename}")
            return FileResponse(
                file_path,
                media_type=safe_mime,
                filename=metadata.name,
                content_disposition_type="attachment",
            )

        if storage_name == "gdrive":
            return StreamingResponse(
                _stream_gdrive(storage, metadata.optional_gfileID),
                media_type=safe_mime,
                headers={"Content-Disposition": _content_disposition(metadata.name)},
            )

        raise HTTPException(status_code=500, detail="Unknown storage backend")

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")


@router.get("/get/{fileid}/{filename}")
async def download_direct(fileid: str, filename: str) -> Response:
    """Direct file download endpoint."""
    return await _download_response(fileid, filename)


@router.put("/{filename:path}")
async def upload(filename: str, request: Request) -> PlainTextResponse:
    """Upload a file via raw PUT body; returns the share URL as plain text.

    The per-file owner key is always returned in the ``X-Owner-Key``
    response header so any client (curl, browser, scripts) can capture it
    at upload time and use it later to issue authenticated ``DELETE``
    requests. The header is never emitted from any other endpoint.
    """
    validate_filename_for_write(filename)

    config = get_config()
    max_size = int(config["host"].get("max_upload_size", DEFAULT_MAX_UPLOAD_SIZE))

    tmp, size = await buffer_request_body(request, max_size=max_size)

    storage = get_storage()
    try:
        metadata = await run_in_threadpool(storage.save, tmp, size, filename)
    finally:
        tmp.close()

    owner_key = metadata.delete
    cache.store_cache(metadata)

    base_url = _resolve_base_url(request, config)
    host = urlparse(base_url).hostname
    if host in ("localhost", "127.0.0.1"):
        print("WARNING: Host URL is not set correctly! Check your proxy settings. (HOST Header)")

    response = PlainTextResponse(f"{base_url}{metadata.id}/{metadata.name}")
    if owner_key:
        response.headers["X-Owner-Key"] = owner_key
    return response


@router.delete(
    "/{fileid}/{filename}",
    responses={
        200: {
            "description": "File removed",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Deleted",
                            "value": {
                                "status": 200,
                                "message": "Deleted",
                                "data": None,
                            },
                        },
                    },
                },
            },
        },
        403: {
            "description": "Owner key missing or incorrect",
            "content": {
                "application/json": {
                    "examples": {
                        "forbidden": {
                            "summary": "Missing or wrong X-Owner-Key",
                            "value": {
                                "status": 403,
                                "message": "Forbidden",
                                "data": None,
                            },
                        },
                    },
                },
            },
        },
        404: {
            "description": "File not found",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {
                            "summary": "Missing fileid or filename",
                            "value": {
                                "status": 404,
                                "message": "Not Found!",
                                "data": None,
                            },
                        },
                    },
                },
            },
        },
    },
)
async def delete_file(
    fileid: str,
    filename: str,
    x_owner_key: str = Header(default=""),
) -> JSONResponse:
    """Permanently remove a file when the caller proves ownership.

    Requires the ``X-Owner-Key`` header to match the key issued at upload
    time. Unlike the retention reaper, user-initiated deletion always
    removes the file immediately regardless of ``delete.permanently``.
    """
    config = get_config()
    validate_fileid(fileid, config["folderidlength"])
    validate_filename_for_read(filename)

    storage = get_storage()
    try:
        metadata = await run_in_threadpool(storage.load_metadata, fileid, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")

    expected = getattr(metadata, "delete", "") or ""
    if not expected or not secrets.compare_digest(x_owner_key, expected):
        raise HTTPException(status_code=403, detail="Forbidden")

    removed = await run_in_threadpool(
        storage.remove, fileid, filename, expected, False, True
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Not Found!")

    cache.invalidate(fileid)
    return make_response(200, "Deleted")


@router.get("/{fileid}/{filename}")
async def share_page(fileid: str, filename: str, request: Request) -> Response:
    """Serve the SPA page for browser clients, or stream the file for curl clients."""
    config = get_config()

    if _is_curl_ua(request):
        return await _download_response(fileid, filename)

    validate_fileid(fileid, config["folderidlength"])
    validate_filename_for_read(filename)

    try:
        await _load_metadata(fileid, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")

    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")
