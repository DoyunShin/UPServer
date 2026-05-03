import asyncio
import html
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from oryups.config import STATIC_DIR, get_config, load_config
from oryups.response import make_response
from oryups.routers import admin, api, api_v1, assets, files, root
from oryups.services.reaper import run_reaper


_BASELINE_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "SAMEORIGIN",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "interest-cohort=()",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach a baseline set of defensive headers to every response.

    The headers harden against MIME sniffing, clickjacking via iframe
    embedding, referrer leakage to third-party hosts, and FLoC-style
    cohort tracking. They're set after the inner app runs so we never
    overwrite headers an endpoint deliberately customized.
    """

    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for header, value in _BASELINE_SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


def _configure_middleware(app: FastAPI, config: dict) -> None:
    """Attach CORS/Proxy middleware based on loaded configuration.

    Must be called BEFORE the first request reaches the app — Starlette
    locks the middleware stack on first ASGI invocation (lifespan startup
    counts), so this happens at module import time, not in the lifespan.

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


def _config_for_module_setup() -> Optional[dict]:
    """Return a loaded config for module-level middleware wiring, if available.

    Two scenarios:
      * CLI launch (``ups`` or any caller that pre-loads via ``load_config``
        before importing this module) — :func:`get_config` returns the
        cached dict and we wire CORS / proxy headers on the spot.
      * Tests / cold imports — config has not been loaded yet; we return
        ``None`` and skip dynamic middleware. Tests don't exercise CORS or
        proxy headers, and the lifespan still loads config for the reaper.

    We deliberately do NOT call :func:`load_config` from here: that would
    eagerly resolve the default config path (or ``UPSERVER_CONFIG`` env
    var) at import time and trigger storage initialization side effects
    (e.g. creating ``local.root``) before the runtime is even configured.
    Operators running ``uvicorn oryups.main:app`` directly without CLI
    pre-loading should set ``UPSERVER_CONFIG`` AND import-load the config
    in their own bootstrap code, mirroring what the ``ups`` CLI does.
    """
    try:
        return get_config()
    except RuntimeError:
        return None


_reaper_task: Optional[asyncio.Task] = None
_reaper_stop: Optional[asyncio.Event] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load configuration (if not already) and manage the reaper task.

    Middleware is installed at module import time, not here — Starlette
    locks the middleware stack once the lifespan starts, so any
    ``app.add_middleware`` call from this scope raises.
    """
    global _reaper_task, _reaper_stop

    load_config()
    cfg = get_config()

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
app.add_middleware(SecurityHeadersMiddleware)

_module_cfg = _config_for_module_setup()
if _module_cfg is not None:
    _configure_middleware(app, _module_cfg)

app.include_router(api.router)
app.include_router(admin.router)
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


_DEFAULT_HINT_BY_STATUS: dict[int, str] = {
    500: "An unexpected error occurred on the server. Please try again later.",
}

_GENERIC_HINT: str = "The resource you were looking for could not be reached."


def _render_error(status_code: int, message: str, hint: str) -> HTMLResponse:
    """Render the static HTML error page with the given status code and message.

    If the ``error.html`` template cannot be read (missing file, permission
    denied, etc.) we emit a minimal inline page so the exception handler never
    re-enters itself. All three substitutions are HTML-escaped as defense in
    depth.
    """
    safe_message = html.escape(message)
    safe_code = html.escape(str(status_code))
    safe_hint = html.escape(hint)
    try:
        template = STATIC_DIR.joinpath("error.html").read_text()
        body = (
            template
            .replace("StatusCode", safe_code)
            .replace("StatusMessage", safe_message)
            .replace("StatusHint", safe_hint)
        )
        return HTMLResponse(body, status_code=status_code)
    except OSError:
        fallback = (
            f"<!doctype html><meta charset=\"utf-8\">"
            f"<title>{safe_code}</title>"
            f"<h1>{safe_code}</h1><p>{safe_message}</p><p>{safe_hint}</p>"
        )
        return HTMLResponse(fallback, status_code=status_code)


def _looks_like_file_share_path(path: str) -> bool:
    """Return True when ``path`` matches the ``/<fileid>/<filename>`` shape.

    Used to distinguish a "file not found / expired" 404 from a "page does
    not exist" 404. We require exactly two non-empty segments and reject
    any path that begins with a reserved app prefix (``/api/``, ``/admin``,
    ``/assets/``, ``/get/``).
    """
    if not path or not path.startswith("/"):
        return False
    if (
        path.startswith("/api/")
        or path.startswith("/admin")
        or path.startswith("/assets/")
        or path.startswith("/get/")
    ):
        return False
    parts = [p for p in path.strip("/").split("/") if p]
    return len(parts) == 2


def _categorize_html_error(
    path: str, status_code: int, message: str
) -> tuple[str, str]:
    """Pick the user-facing message and hint for an HTML error page.

    The two flavors of 404 are split here so the rendered page can
    explain whether a *page* or a *file* could not be found.

    Args:
        path(str): The request path that produced the error.
        status_code(int): HTTP status code being rendered.
        message(str): Original ``HTTPException.detail`` (used as a fallback
            when no category-specific copy exists).

    Return:
        message_and_hint(tuple[str, str]): The message line and hint line
        to inject into the template.
    """
    if status_code == 404:
        if _looks_like_file_share_path(path):
            return (
                "File not found",
                "This file may have been removed, expired, or never existed.",
            )
        return (
            "Page not found",
            "The page you were looking for does not exist on this server.",
        )
    hint = _DEFAULT_HINT_BY_STATUS.get(status_code, _GENERIC_HINT)
    return message, hint


def _build_error_response(
    request: Request,
    status_code: int,
    message: str,
    extra_headers: Optional[dict[str, str]] = None,
) -> Response:
    """Pick the right error representation (plain text / envelope / HTML) for a request.

    Optional ``extra_headers`` are merged into the outgoing response, so
    handlers that raise ``HTTPException(..., headers=...)`` (e.g. the
    admin endpoint emitting ``Cache-Control: no-store``) keep their
    headers across this central rewrite.
    """
    if _is_curl_ua(request):
        response: Response = PlainTextResponse(f"{status_code}: {message}", status_code=status_code)
    elif _is_api_path(request.url.path) or request.method == "DELETE":
        response = make_response(status_code, message)
    else:
        # A browser GET that hits a route only registered for other methods
        # surfaces as 405; from the user's perspective the URL just does
        # not have a page, so render it as a "page not found" 404.
        html_status = status_code
        if html_status == 405 and request.method == "GET":
            html_status = 404
        rendered_message, hint = _categorize_html_error(
            request.url.path, html_status, message
        )
        response = _render_error(html_status, rendered_message, hint)
    if extra_headers:
        for header, value in extra_headers.items():
            response.headers[header] = value
    return response


@app.exception_handler(StarletteHTTPException)
async def on_http_exception(request: Request, exc: StarletteHTTPException) -> Response:
    """Uniform HTTPException handler aware of API / curl / browser clients.

    Registered on Starlette's base ``HTTPException`` so it also catches
    routing-layer errors (e.g. 404 for unknown paths and 405 when only
    other methods are registered) which are raised before any route's
    own ``fastapi.HTTPException`` ever runs.
    """
    return _build_error_response(
        request,
        exc.status_code,
        str(exc.detail),
        getattr(exc, "headers", None),
    )


def _scrub_validation_errors(errors: list[dict]) -> list[dict]:
    """Replace non-finite numeric inputs in Pydantic errors with their repr.

    Pydantic includes the offending input value under ``input``. Floats
    like ``NaN``/``Infinity`` are valid Python objects but cannot survive
    the response JSON encoder (``allow_nan=False``) — without this scrub
    the validation 422 turns into a 500.
    """
    import math

    scrubbed: list[dict] = []
    for err in errors:
        item = dict(err)
        val = item.get("input")
        if isinstance(val, float) and not math.isfinite(val):
            item["input"] = repr(val)
        scrubbed.append(item)
    return scrubbed


@app.exception_handler(RequestValidationError)
async def on_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return validation errors using the envelope."""
    return make_response(422, "Validation error", _scrub_validation_errors(exc.errors()))


@app.exception_handler(Exception)
async def on_unhandled_exception(request: Request, exc: Exception) -> Response:
    """Catch-all handler: 500 with the proper representation for the caller."""
    return _build_error_response(request, 500, "Internal Server Error!")
