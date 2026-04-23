from tempfile import SpooledTemporaryFile
from typing import IO, Optional, Tuple

from fastapi import HTTPException, Request

SPOOL_THRESHOLD: int = 10 * 1024 * 1024


def _parse_content_length(header_value: Optional[str]) -> Optional[int]:
    """Parse a Content-Length header into an int. Returns None when absent."""
    if header_value is None:
        return None
    try:
        value = int(header_value)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Content-Length")
    if value < 0:
        raise HTTPException(status_code=400, detail="Invalid Content-Length")
    return value


async def buffer_request_body(
    request: Request,
    *,
    max_size: Optional[int] = None,
) -> Tuple[IO[bytes], int]:
    """Buffer a raw request body into a SpooledTemporaryFile.

    Reads the incoming PUT body chunk-by-chunk so memory usage stays bounded;
    files larger than SPOOL_THRESHOLD spill to disk automatically. When
    ``max_size`` is set, both the declared Content-Length and the actual
    received byte count are enforced.

    Args:
        request(fastapi.Request): Incoming request with a streamable body.
        max_size(int, optional): Maximum accepted body size in bytes.

    Return:
        result(tuple[IO[bytes], int]): (file-like object positioned at 0,
            total size in bytes).

    Raises:
        HTTPException: 400 on a malformed Content-Length header; 413 when the
            body exceeds ``max_size``.
    """
    declared = _parse_content_length(request.headers.get("content-length"))
    if max_size is not None and declared is not None and declared > max_size:
        raise HTTPException(status_code=413, detail="Payload Too Large")

    tmp: SpooledTemporaryFile = SpooledTemporaryFile(max_size=SPOOL_THRESHOLD)
    size = 0
    try:
        async for chunk in request.stream():
            if not chunk:
                continue
            size += len(chunk)
            if max_size is not None and size > max_size:
                raise HTTPException(status_code=413, detail="Payload Too Large")
            tmp.write(chunk)
        tmp.seek(0)
        return tmp, size
    except BaseException:
        tmp.close()
        raise
