from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from oryups.response import make_response
from oryups.services import cache

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
    },
)
async def clearcache() -> JSONResponse:
    """Evict expired metadata entries from the in-memory cache."""
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
    try:
        metadata = cache.load_metadata(fileid, filename)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Not Found!")
    return make_response(200, "OK", metadata.to_dict())
