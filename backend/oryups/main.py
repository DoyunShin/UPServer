import asyncio
import html
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from oryups.config import STATIC_DIR, get_config, load_config
from oryups.response import make_response
from oryups.routers import api, api_v1, assets, files, root
from oryups.services.reaper import run_reaper


def _configure_middleware(app: FastAPI, config: dict) -> None:
    """Attach CORS/Proxy middleware based on loaded configuration.

    Safe defaults: if ``host.cors_origins`` is empty, no CORS middleware is
    installed; if it's ``["*"]``, credentials are disabled per the Fetch
    specification. Proxy-header trust is limited to ``host.proxy_trusted_hosts``
    (defaults to localhost).
    """
    cors_origins = config["host"].get("cors_origins", []) or []
    if cors_origins:
        if list(cors_origins) == ["*"]:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=False,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["X-Owner-Key"],
            )
        else:
            app.add_middleware(
                CORSMiddleware,
                allow_origins=list(cors_origins),
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
                expose_headers=["X-Owner-Key"],
            )

    if config["host"].get("proxy", False):
        from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

        trusted = config["host"].get("proxy_trusted_hosts", "127.0.0.1")
        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted)


_reaper_task: Optional[asyncio.Task] = None
_reaper_stop: Optional[asyncio.Event] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load configuration, initialize middleware, and manage the reaper task."""
    global _reaper_task, _reaper_stop

    load_config()
    cfg = get_config()
    _configure_middleware(app, cfg)

    delete_rule = cfg.get("delete", {})
    if delete_rule.get("enabled") and delete_rule.get("permanently"):
        _reaper_stop = asyncio.Event()
        _reaper_task = asyncio.create_task(run_reaper(_reaper_stop))
    else:
        _reaper_stop = None
        _reaper_task = None

    try:
        yield
    finally:
        if _reaper_task is not None and _reaper_stop is not None:
            _reaper_stop.set()
            try:
                await asyncio.wait_for(_reaper_task, timeout=5)
            except asyncio.TimeoutError:
                _reaper_task.cancel()
            except Exception:
                pass
        _reaper_task = None
        _reaper_stop = None


app = FastAPI(title="UPServer", lifespan=lifespan)

app.include_router(api.router)
app.include_router(api_v1.router)
app.include_router(assets.router)
app.include_router(root.router)
app.include_router(files.router)


def _is_api_path(path: str) -> bool:
    """Return True for paths whose responses should use the JSON envelope."""
    return path.startswith("/api/")


def _is_curl_ua(request: Request) -> bool:
    """Detect whether the request User-Agent looks like curl."""
    return "curl" in request.headers.get("user-agent", "")


def _render_error(status_code: int, message: str) -> HTMLResponse:
    """Render the static HTML error page with the given status code and message.

    If the ``error.html`` template cannot be read (missing file, permission
    denied, etc.) we emit a minimal inline page so the exception handler never
    re-enters itself. Both substitutions are HTML-escaped as defense in depth.
    """
    safe_message = html.escape(message)
    safe_code = html.escape(str(status_code))
    try:
        template = STATIC_DIR.joinpath("error.html").read_text()
        body = template.replace("StatusCode", safe_code).replace("StatusMessage", safe_message)
        return HTMLResponse(body, status_code=status_code)
    except OSError:
        fallback = (
            f"<!doctype html><meta charset=\"utf-8\">"
            f"<title>{safe_code}</title>"
            f"<h1>{safe_code}</h1><p>{safe_message}</p>"
        )
        return HTMLResponse(fallback, status_code=status_code)


def _build_error_response(request: Request, status_code: int, message: str) -> Response:
    """Pick the right error representation (plain text / envelope / HTML) for a request."""
    if _is_curl_ua(request):
        return PlainTextResponse(f"{status_code}: {message}", status_code=status_code)
    if _is_api_path(request.url.path) or request.method == "DELETE":
        return make_response(status_code, message)
    return _render_error(status_code, message)


@app.exception_handler(HTTPException)
async def on_http_exception(request: Request, exc: HTTPException) -> Response:
    """Uniform HTTPException handler aware of API / curl / browser clients."""
    return _build_error_response(request, exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation errors using the envelope."""
    return make_response(422, "Validation error", exc.errors())


@app.exception_handler(Exception)
async def on_unhandled_exception(request: Request, exc: Exception) -> Response:
    """Catch-all handler: 500 with the proper representation for the caller."""
    return _build_error_response(request, 500, "Internal Server Error!")
