from io import BytesIO
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import (
    FileResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)

from oryups.config import STATIC_DIR, get_config, get_storage
from oryups.services import cache
from oryups.utils.upload import buffer_request_body
from oryups.utils.validation import (
    validate_fileid,
    validate_filename_for_read,
    validate_filename_for_write,
)

DEFAULT_MAX_UPLOAD_SIZE: int = 1 << 30

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


async def _download_response(fileid: str, filename: str) -> Response:
    """Build the file download response using the configured storage backend."""
    config = get_config()
    validate_fileid(fileid, config["folderidlength"])
    validate_filename_for_read(filename)

    storage = get_storage()

    try:
        if storage.cache and storage.is_cached(fileid, filename):
            cached_path = storage.get_cached(fileid, filename)
            metadata = cache.load_metadata(fileid, filename)
            return FileResponse(cached_path, media_type=metadata.mimeType, filename=metadata.name)

        if config["host"]["cdn"]["enabled"]:
            cdn_url = config["host"]["cdn"]["url"].rstrip("/")
            return RedirectResponse(f"{cdn_url}/{fileid}/{filename}")

        metadata = cache.load_metadata(fileid, filename)
        storage_name = config["storage"]

        if storage_name == "local":
            file_path = storage.root / fileid / filename
            if not file_path.is_file():
                raise FileNotFoundError(f"{fileid}/{filename}")
            return FileResponse(file_path, media_type=metadata.mimeType, filename=metadata.name)

        if storage_name == "gdrive":
            data = await run_in_threadpool(
                lambda: storage.service.files()
                .get_media(fileId=metadata.optional_gfileID)
                .execute()
            )
            return StreamingResponse(BytesIO(data), media_type=metadata.mimeType)

        raise HTTPException(status_code=500, detail="Unknown storage backend")

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")


@router.get("/get/{fileid}/{filename}")
async def download_direct(fileid: str, filename: str) -> Response:
    """Direct file download endpoint."""
    return await _download_response(fileid, filename)


@router.put("/{filename:path}")
async def upload(filename: str, request: Request) -> PlainTextResponse:
    """Upload a file via raw PUT body; returns the share URL as plain text."""
    validate_filename_for_write(filename)

    config = get_config()
    max_size = int(config["host"].get("max_upload_size", DEFAULT_MAX_UPLOAD_SIZE))

    tmp, size = await buffer_request_body(request, max_size=max_size)

    storage = get_storage()
    try:
        metadata = await run_in_threadpool(storage.save, tmp, size, filename)
    finally:
        tmp.close()
    cache.store_cache(metadata)

    base_url = _resolve_base_url(request, config)
    host = urlparse(base_url).hostname
    if host in ("localhost", "127.0.0.1"):
        print("WARNING: Host URL is not set correctly! Check your proxy settings. (HOST Header)")

    return PlainTextResponse(f"{base_url}{metadata.id}/{metadata.name}")


@router.get("/{fileid}/{filename}")
async def share_page(fileid: str, filename: str, request: Request) -> Response:
    """Serve the SPA page for browser clients, or stream the file for curl clients."""
    config = get_config()

    if _is_curl_ua(request):
        return await _download_response(fileid, filename)

    validate_fileid(fileid, config["folderidlength"])
    validate_filename_for_read(filename)

    try:
        cache.load_metadata(fileid, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")

    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")
