from fastapi import APIRouter
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse

from oryups.config import STATIC_DIR, get_config

router = APIRouter(tags=["Root"])


@router.get("/", include_in_schema=False)
@router.post("/", include_in_schema=False)
async def index() -> FileResponse:
    """Serve the main SPA/index page."""
    return FileResponse(STATIC_DIR / "index.html", media_type="text/html")


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> RedirectResponse:
    """Redirect favicon requests to the configured icon URL."""
    return RedirectResponse(get_config()["general"]["icon"])


@router.get("/index.html", include_in_schema=False)
async def index_html_redirect() -> RedirectResponse:
    """Canonicalize /index.html to /."""
    return RedirectResponse("/")


@router.get("/robots.txt", include_in_schema=False)
async def robots() -> PlainTextResponse:
    """Disallow all crawlers."""
    return PlainTextResponse("Disallow: /")
