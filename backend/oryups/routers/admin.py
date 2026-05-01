import secrets

from fastapi import APIRouter, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from oryups.config import get_config
from oryups.response import make_response
from oryups.services import admin, admin_session


router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])


_NO_STORE_HEADERS: dict[str, str] = {
    "Cache-Control": "no-store",
    "Vary": "Authorization",
}


class AdminLoginRequest(BaseModel):
    """Request body for ``POST /api/v1/admin/login``.

    Args:
        password(str): The shared admin password from ``host.admin_token``.
    """

    password: str

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"password": "admin1414"},
            ],
        },
    }


def _extract_bearer_token(authorization: str) -> str:
    """Pull the bearer value out of an ``Authorization`` header.

    Args:
        authorization(str): The raw header value.

    Return:
        token(str): The token portion when the scheme is exactly ``Bearer``
        (case-insensitive); empty string otherwise.
    """
    if not authorization:
        return ""
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


def is_admin_authorized(authorization: str) -> bool:
    """Return True when the supplied ``Authorization`` header is a valid bearer.

    Non-raising counterpart used by other routers to grant read access to
    expired files (and any other admin-only override) without short-
    circuiting their own success/error flow.

    Args:
        authorization(str): The raw value of the ``Authorization`` header.

    Return:
        valid(bool): True when admin auth is configured AND the supplied
        bearer token is registered and not yet expired.
    """
    admin_token = get_config()["host"].get("admin_token", "")
    if not admin_token:
        return False
    token = _extract_bearer_token(authorization)
    return admin_session.validate_token(token)


def _ensure_admin_enabled() -> None:
    """Raise 404 when ``host.admin_token`` is not configured."""
    admin_token = get_config()["host"].get("admin_token", "")
    if not admin_token:
        raise HTTPException(
            status_code=404,
            detail="Not Found!",
            headers=_NO_STORE_HEADERS,
        )


def _verify_authorization(authorization: str) -> None:
    """Reject the request unless the bearer token is valid and unexpired.

    404 when admin is disabled (no ``host.admin_token`` set), 401 when the
    bearer is missing/wrong/expired. Both responses carry ``Cache-Control:
    no-store`` so intermediaries cannot retain or replay them.
    """
    _ensure_admin_enabled()
    token = _extract_bearer_token(authorization)
    if not admin_session.validate_token(token):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers=_NO_STORE_HEADERS,
        )


def _verify_password(password: str) -> None:
    """Reject the login attempt unless the password matches the configured token.

    404 when admin is disabled, 403 when the password is wrong. Constant-
    time comparison prevents timing leaks of the configured value.
    """
    admin_token = get_config()["host"].get("admin_token", "")
    if not admin_token:
        raise HTTPException(
            status_code=404,
            detail="Not Found!",
            headers=_NO_STORE_HEADERS,
        )
    if not secrets.compare_digest(password or "", admin_token):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
            headers=_NO_STORE_HEADERS,
        )


def _attach_no_store(response: JSONResponse) -> JSONResponse:
    """Apply the admin cache guards in-place and return the same response."""
    for header, value in _NO_STORE_HEADERS.items():
        response.headers[header] = value
    return response


@router.post(
    "/login",
    responses={
        200: {
            "description": "Bearer token issued",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Login OK",
                            "value": {
                                "status": 200,
                                "message": "OK",
                                "data": {
                                    "token": "F8sQ-...redacted...32chars",
                                    "expires_at": 1761601800.0,
                                    "ttl_seconds": 1800,
                                },
                            },
                        },
                    },
                },
            },
        },
        403: {
            "description": "Wrong password",
            "content": {
                "application/json": {
                    "examples": {
                        "forbidden": {
                            "summary": "Password mismatch",
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
            "description": "Admin disabled",
            "content": {
                "application/json": {
                    "examples": {
                        "disabled": {
                            "summary": "admin_token not set in config",
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
async def post_admin_login(body: AdminLoginRequest) -> JSONResponse:
    """Exchange the configured admin password for a short-lived bearer token.

    On success the response carries ``token`` (opaque 32-byte URL-safe
    string), ``expires_at`` (unix seconds), and ``ttl_seconds`` so the
    client can decide when to re-authenticate. The token is held in
    process memory only — every server restart invalidates every active
    session.
    """
    _verify_password(body.password)
    token, expires_at = admin_session.issue_token()
    return _attach_no_store(
        make_response(
            200,
            "OK",
            {
                "token": token,
                "expires_at": expires_at,
                "ttl_seconds": admin_session.TOKEN_TTL_SECONDS,
            },
        )
    )


@router.post(
    "/logout",
    responses={
        200: {
            "description": "Token revoked (idempotent)",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Logout OK",
                            "value": {
                                "status": 200,
                                "message": "OK",
                                "data": None,
                            },
                        },
                    },
                },
            },
        },
        404: {
            "description": "Admin disabled",
            "content": {
                "application/json": {
                    "examples": {
                        "disabled": {
                            "summary": "admin_token not set in config",
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
async def post_admin_logout(
    authorization: str = Header(default=""),
) -> JSONResponse:
    """Revoke the bearer token carried in ``Authorization``.

    Idempotent: returns 200 even if the token is already absent or
    expired. Returns 404 when admin auth is disabled. We deliberately do
    not require a valid bearer to call this endpoint — making logout
    work with a stale token is friendlier and reveals nothing.
    """
    _ensure_admin_enabled()
    token = _extract_bearer_token(authorization)
    admin_session.revoke_token(token)
    return _attach_no_store(make_response(200, "OK"))


@router.get(
    "/files",
    responses={
        200: {
            "description": "Active and expired-but-still-present files",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "File listing",
                            "value": {
                                "status": 200,
                                "message": "OK",
                                "data": {
                                    "active": [
                                        {
                                            "id": "abc123",
                                            "name": "hello.txt",
                                            "mimeType": "text/plain",
                                            "size": 1234,
                                            "hidden": False,
                                            "created_at": 1761000000.0,
                                            "delete_after": 604800.0,
                                            "expires_at": 1761604800.0,
                                            "expired": False,
                                        },
                                    ],
                                    "expired": [
                                        {
                                            "id": "def456",
                                            "name": "old.bin",
                                            "mimeType": "application/octet-stream",
                                            "size": 4096,
                                            "hidden": False,
                                            "created_at": 1750000000.0,
                                            "delete_after": 604800.0,
                                            "expires_at": 1750604800.0,
                                            "expired": True,
                                        },
                                    ],
                                },
                            },
                        },
                    },
                },
            },
        },
        401: {
            "description": "Bearer missing, wrong, or expired",
            "content": {
                "application/json": {
                    "examples": {
                        "unauthorized": {
                            "summary": "Re-login required",
                            "value": {
                                "status": 401,
                                "message": "Unauthorized",
                                "data": None,
                            },
                        },
                    },
                },
            },
        },
        404: {
            "description": "Endpoint disabled (no admin token configured)",
            "content": {
                "application/json": {
                    "examples": {
                        "disabled": {
                            "summary": "admin_token not set in config",
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
        500: {
            "description": "Storage enumeration failed",
            "content": {
                "application/json": {
                    "examples": {
                        "storage_error": {
                            "summary": "Backend listing raised an exception",
                            "value": {
                                "status": 500,
                                "message": "Internal Server Error!",
                                "data": None,
                            },
                        },
                    },
                },
            },
        },
    },
)
async def get_admin_files(
    authorization: str = Header(default=""),
) -> JSONResponse:
    """List every file held by the storage backend, split by retention state.

    Requires a valid bearer token issued by ``POST /api/v1/admin/login``.
    """
    _verify_authorization(authorization)
    try:
        data = await run_in_threadpool(admin.list_all_files)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Internal Server Error!",
            headers=_NO_STORE_HEADERS,
        )
    return _attach_no_store(make_response(200, "OK", data))
