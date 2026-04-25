import secrets

from fastapi import APIRouter, Header, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from oryups.config import get_config
from oryups.response import make_response
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
async def get_metadata(fileid: str, filename: str) -> JSONResponse:
    """Return metadata for a stored file by (fileid, filename)."""
    folder_length = get_config()["folderidlength"]
    validate_fileid(fileid, folder_length)
    validate_filename_for_read(filename)
    try:
        metadata = await run_in_threadpool(cache.load_metadata, fileid, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")
    return make_response(200, "OK", metadata.to_dict(public=True))
