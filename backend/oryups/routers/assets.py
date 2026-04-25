from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from oryups.config import ASSETS_DIR

router = APIRouter(tags=["Assets"])


@router.get("/assets/{path:path}")
async def serve_asset(path: str) -> FileResponse:
    """Serve a static asset file from the backend/static/assets directory."""
    target = (ASSETS_DIR / path).resolve()
    try:
        target.relative_to(ASSETS_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=404, detail="Not Found!")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Not Found!")
    return FileResponse(target)
