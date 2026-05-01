import secrets

from fastapi import APIRouter, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from oryups.config import get_config, get_storage
from oryups.response import make_response
from oryups.routers.admin import authorize_admin_optional, is_admin_authorized
from oryups.services import cache
from oryups.utils.validation import validate_fileid, validate_filename_for_read

router = APIRouter(prefix="/api/v1", tags=["ApiV1"])


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
