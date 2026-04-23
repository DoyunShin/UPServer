from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from oryups.config import STATIC_DIR, get_config, load_config
from oryups.response import make_response
from oryups.routers import api, api_v1, assets, files, root


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load configuration and initialize storage on startup."""
    load_config()
    config = get_config()
    if config["host"]["proxy"]:
        from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

        app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")
    yield


app = FastAPI(title="UPServer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    """Render the static HTML error page with the given status code and message."""
    template = STATIC_DIR.joinpath("error.html").read_text()
    body = template.replace("StatusCode", str(status_code)).replace("StatusMessage", message)
    return HTMLResponse(body, status_code=status_code)


def _build_error_response(request: Request, status_code: int, message: str) -> Response:
    """Pick the right error representation (plain text / envelope / HTML) for a request."""
    if _is_curl_ua(request):
        return PlainTextResponse(f"{status_code}: {message}", status_code=status_code)
    if _is_api_path(request.url.path):
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
