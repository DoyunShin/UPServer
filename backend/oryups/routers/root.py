from urllib.parse import urlparse

from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse, Response

from oryups.config import STATIC_DIR, get_config

router = APIRouter(tags=["Root"])

_LOCAL_FAVICON = STATIC_DIR / "assets" / "img" / "favicon.svg"


def _safe_icon_target(raw: object) -> str | None:
    """Return the icon URL only when it's a safe scheme to redirect to.

    Accepts ``http``/``https`` absolute URLs, protocol-relative ``//host``
    (rewritten to ``https:``), and same-origin paths starting with ``/``.
    Anything else (empty, javascript:, data:, malformed) returns ``None``
    so the caller can fall back to a locally-served asset.
    """
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    if any(ch in value for ch in "\r\n\t"):
        return None
    if value.startswith("//"):
        return "https:" + value
    if value.startswith("/"):
        return value
    parsed = urlparse(value)
    if parsed.scheme in ("http", "https") and parsed.netloc:
        return value
    return None


@router.get("/", include_in_schema=False)
@router.post("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the main SPA/index page."""
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@router.get("/admin", include_in_schema=False)
@router.get("/admin/{path:path}", include_in_schema=False)
async def get_admin_page(path: str = "") -> FileResponse:
    """Serve the SPA so any SvelteKit ``/admin/...`` route can take over.

    The single-segment path ``/admin`` does not match
    ``/{fileid}/{filename}`` in :mod:`oryups.routers.files`, and a
    three-segment admin file path like ``/admin/<id>/<name>`` does not
    match anything else either. We therefore route the entire ``/admin``
    subtree to the SPA shell.
    """
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> Response:
    """Serve the favicon, validating any operator-configured override.

    If ``general.icon`` is a safe http(s) URL or same-origin path we issue
    a redirect; otherwise we serve the bundled SVG directly so a misconfig
    cannot turn this endpoint into an open redirect or a referrer leak.
    """
    target = _safe_icon_target(get_config().get("general", {}).get("icon"))
    if target is not None:
        return RedirectResponse(target)
    if _LOCAL_FAVICON.is_file():
        return FileResponse(_LOCAL_FAVICON, media_type="image/svg+xml")
    return Response(status_code=404)


@router.get("/index.html", include_in_schema=False)
async def index_html_redirect() -> RedirectResponse:
    """Canonicalize /index.html to /."""
    return RedirectResponse("/")


@router.get("/robots.txt", include_in_schema=False)
async def robots() -> PlainTextResponse:
    """Disallow all crawlers."""
    return PlainTextResponse("Disallow: /")
