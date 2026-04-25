import re

from fastapi import HTTPException

FILEID_RE = re.compile(r"^[A-Za-z0-9]+$")
MAX_FILENAME_LENGTH: int = 255
_INVALID_FILENAME_CHARS: tuple[str, ...] = ("/", "\\", "\x00")


def validate_fileid(fileid: str, expected_length: int) -> None:
    """Validate a file id against the configured length and character set.

    Args:
        fileid(str): File id from the URL path.
        expected_length(int): Required length (from ``config["folderidlength"]``).

    Raises:
        HTTPException: 404 if the id is malformed.
    """
    if len(fileid) != expected_length or not FILEID_RE.fullmatch(fileid):
        raise HTTPException(status_code=404, detail="Not Found!")


def _has_invalid_filename_chars(filename: str) -> bool:
    return any(c in filename for c in _INVALID_FILENAME_CHARS)


def validate_filename_for_read(filename: str) -> None:
    """Validate a filename used on a read path. Failures return 404."""
    if not filename or len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(status_code=404, detail="Not Found!")
    if filename.startswith(".") or _has_invalid_filename_chars(filename):
        raise HTTPException(status_code=404, detail="Not Found!")


def validate_filename_for_write(filename: str) -> None:
    """Validate a filename used on the PUT path. Failures return 400."""
    if not filename or len(filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(status_code=400, detail="Invalid path")
    if filename.startswith(".") or _has_invalid_filename_chars(filename):
        raise HTTPException(status_code=400, detail="Invalid path")
