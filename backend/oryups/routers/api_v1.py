import secrets

from fastapi import APIRouter, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from oryups.config import get_config, get_storage
from oryups.response import make_response
from oryups.routers.admin import (
    _attach_no_store,
    _verify_authorization,
    authorize_admin_optional,
    is_admin_authorized,
)
from oryups.services import admin as admin_service
from oryups.services import cache
from oryups.utils.validation import validate_fileid, validate_filename_for_read

router = APIRouter(prefix="/api/v1", tags=["ApiV1"])


class UpdateExpiryRequest(BaseModel):
    """Request body for ``PATCH /api/v1/{fileid}/{filename}``.

    Args:
        delete_after(float): New retention window in seconds. ``-1``
            marks the file as never-expires; ``0`` means immediate
            expiry; positive values are seconds from ``created_at``.
    """

    delete_after: float = Field(..., ge=-1.0, allow_inf_nan=False)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {"delete_after": 604800},
                {"delete_after": -1},
                {"delete_after": 0},
            ],
        },
    }


@router.get(
    "/clearcache",
    responses={
        200: {
            "description": "Expired cache entries cleared",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Cache cleared",
                            "value": {
                                "status": 200,
                                "message": "Cache cleared",
                                "data": None,
                            },
                        },
                    },
                },
            },
        },
        403: {
            "description": "Admin token mismatch",
            "content": {
                "application/json": {
                    "examples": {
                        "forbidden": {
                            "summary": "Missing or wrong X-Admin-Token",
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
    },
)
async def clearcache(
    x_admin_token: str = Header(default=""),
) -> JSONResponse:
    """Evict expired metadata entries from the in-memory cache.

    Requires the ``X-Admin-Token`` header to match ``host.admin_token``. When
    ``admin_token`` is empty the endpoint is disabled and returns 404.
    """
    admin_token = get_config()["host"].get("admin_token", "")
    if not admin_token:
        raise HTTPException(status_code=404, detail="Not Found!")
    if not secrets.compare_digest(x_admin_token, admin_token):
        raise HTTPException(status_code=403, detail="Forbidden")
    cache.clear_cache()
    return make_response(200, "Cache cleared")


@router.get(
    "/{fileid}/{filename}",
    responses={
        200: {
            "description": "File metadata",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Metadata retrieved",
                            "value": {
                                "status": 200,
                                "message": "OK",
                                "data": {
                                    "id": "abc123",
                                    "name": "hello.txt",
                                    "mimeType": "text/plain",
                                    "size": 1234,
                                    "hidden": False,
                                    "created_at": 1700000000.0,
                                    "delete_after": 3600.0,
                                },
                            },
                        },
                    },
                },
            },
        },
        401: {
            "description": "Authorization header present but invalid",
            "content": {
                "application/json": {
                    "examples": {
                        "unauthorized": {
                            "summary": "Stale or wrong admin bearer",
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
async def get_metadata(
    fileid: str,
    filename: str,
    authorization: str = Header(default=""),
) -> JSONResponse:
    """Return metadata for a stored file by (fileid, filename).

    A valid admin bearer in ``Authorization: Bearer <token>`` bypasses
    the retention check, so operators can still inspect files that have
    already expired and now return 404 to the public.
    """
    folder_length = get_config()["folderidlength"]
    validate_fileid(fileid, folder_length)
    validate_filename_for_read(filename)
    bypass_expiry = authorize_admin_optional(authorization)
    try:
        metadata = await run_in_threadpool(
            lambda: cache.load_metadata(fileid, filename, bypass_expiry=bypass_expiry)
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")
    return make_response(200, "OK", metadata.to_dict())


@router.delete(
    "/{fileid}/{filename}",
    responses={
        200: {
            "description": "File permanently removed",
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
        401: {
            "description": "Authorization header present but invalid",
            "content": {
                "application/json": {
                    "examples": {
                        "unauthorized": {
                            "summary": "Stale or wrong admin bearer",
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
        403: {
            "description": "Neither owner key nor admin bearer is valid",
            "content": {
                "application/json": {
                    "examples": {
                        "forbidden": {
                            "summary": "Missing or wrong credentials",
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
    authorization: str = Header(default=""),
) -> JSONResponse:
    """Permanently remove a file.

    Accepts either credential:

    * ``X-Owner-Key`` matching the key issued at upload time.
    * ``Authorization: Bearer <admin-token>`` for an authenticated admin.

    Either one is sufficient. Removal is always permanent regardless of
    ``delete.permanently`` — both the file folder and its metadata
    sidecar are wiped from storage.
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
    is_admin = authorize_admin_optional(authorization)
    is_owner = bool(expected) and secrets.compare_digest(x_owner_key, expected)
    if not (is_admin or is_owner):
        raise HTTPException(status_code=403, detail="Forbidden")

    removed = await run_in_threadpool(
        storage.remove, fileid, filename, expected, is_admin, True
    )
    if not removed:
        raise HTTPException(status_code=404, detail="Not Found!")

    cache.invalidate(fileid)
    return make_response(200, "Deleted")


@router.patch(
    "/{fileid}/{filename}",
    responses={
        200: {
            "description": "Expiry updated",
            "content": {
                "application/json": {
                    "examples": {
                        "extended": {
                            "summary": "Retention extended",
                            "value": {
                                "status": 200,
                                "message": "Updated",
                                "data": {
                                    "id": "abc123",
                                    "name": "hello.txt",
                                    "mimeType": "text/plain",
                                    "size": 1234,
                                    "hidden": False,
                                    "created_at": 1700000000.0,
                                    "delete_after": 604800.0,
                                },
                            },
                        },
                        "never": {
                            "summary": "Pinned to never expire",
                            "value": {
                                "status": 200,
                                "message": "Updated",
                                "data": {
                                    "id": "abc123",
                                    "name": "hello.txt",
                                    "mimeType": "text/plain",
                                    "size": 1234,
                                    "hidden": False,
                                    "created_at": 1700000000.0,
                                    "delete_after": -1.0,
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
            "description": "Admin disabled, or file not found",
            "content": {
                "application/json": {
                    "examples": {
                        "admin_disabled": {
                            "summary": "host.admin_token not set",
                            "value": {
                                "status": 404,
                                "message": "Not Found!",
                                "data": None,
                            },
                        },
                        "file_missing": {
                            "summary": "fileid or filename does not exist",
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
        422: {
            "description": "Validation failure",
            "content": {
                "application/json": {
                    "examples": {
                        "below_sentinel": {
                            "summary": "delete_after < -1",
                            "value": {
                                "status": 422,
                                "message": "Validation error",
                                "data": [
                                    {
                                        "loc": ["body", "delete_after"],
                                        "msg": "Input should be greater than or equal to -1",
                                        "type": "greater_than_equal",
                                    }
                                ],
                            },
                        },
                        "non_finite": {
                            "summary": "NaN or Infinity rejected",
                            "value": {
                                "status": 422,
                                "message": "Validation error",
                                "data": [
                                    {
                                        "loc": ["body", "delete_after"],
                                        "msg": "Input is not a finite number",
                                        "type": "finite_number",
                                    }
                                ],
                            },
                        },
                        "wrong_type": {
                            "summary": "delete_after is not a number",
                            "value": {
                                "status": 422,
                                "message": "Validation error",
                                "data": [
                                    {
                                        "loc": ["body", "delete_after"],
                                        "msg": "Input should be a valid number",
                                        "type": "float_parsing",
                                    }
                                ],
                            },
                        },
                    },
                },
            },
        },
    },
)
async def update_file_expiry(
    fileid: str,
    filename: str,
    body: UpdateExpiryRequest,
    authorization: str = Header(default=""),
) -> JSONResponse:
    """Update the ``delete_after`` of a stored file.

    Requires a valid admin bearer token. Owner key is intentionally not
    accepted — only operators may change retention windows. ``-1``
    marks the file as never-expires; non-negative values are retention
    seconds (``0`` means immediate expiry).
    """
    _verify_authorization(authorization)
    config = get_config()
    validate_fileid(fileid, config["folderidlength"])
    validate_filename_for_read(filename)

    try:
        metadata = await run_in_threadpool(
            admin_service.update_file_expiry, fileid, filename, body.delete_after
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    return _attach_no_store(
        make_response(200, "Updated", metadata.to_dict(private=False))
    )
