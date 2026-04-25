from fastapi import APIRouter
from fastapi.responses import JSONResponse

from oryups.config import get_config
from oryups.response import make_response

router = APIRouter(prefix="/api", tags=["Api"])


@router.get(
    "/info",
    responses={
        200: {
            "description": "Public server info",
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Info retrieved",
                            "value": {
                                "status": 200,
                                "message": "OK",
                                "data": {
                                    "name": "Example's Upload",
                                    "brand": "Somebody",
                                    "info": "Working as <strong>Server Admin</strong>",
                                    "icon": "//example.com/favicon.ico",
                                    "contact": "//example.com/contact",
                                    "webinfo": [],
                                },
                            },
                        },
                    },
                },
            },
        },
    },
)
async def info() -> JSONResponse:
    """Return public-facing server info from ``config["general"]``."""
    return make_response(200, "OK", get_config()["general"])
