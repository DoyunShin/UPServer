from tempfile import SpooledTemporaryFile
from typing import IO, Tuple

from fastapi import Request

SPOOL_THRESHOLD: int = 10 * 1024 * 1024


async def buffer_request_body(request: Request) -> Tuple[IO[bytes], int]:
    """Buffer a raw request body into a SpooledTemporaryFile.

    Reads the incoming PUT body chunk-by-chunk so memory usage stays bounded;
    files larger than SPOOL_THRESHOLD spill to disk automatically.

    Args:
        request(fastapi.Request): Incoming request with a streamable body.

    Return:
        result(tuple[IO[bytes], int]): (file-like object positioned at 0, total size in bytes).
    """
    tmp: SpooledTemporaryFile = SpooledTemporaryFile(max_size=SPOOL_THRESHOLD)
    size = 0
    async for chunk in request.stream():
        if not chunk:
            continue
        tmp.write(chunk)
        size += len(chunk)
    tmp.seek(0)
    return tmp, size
