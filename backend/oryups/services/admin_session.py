import secrets
import threading
import time


TOKEN_TTL_SECONDS: int = 1800

_tokens: dict[str, float] = {}
_lock: threading.Lock = threading.Lock()


def issue_token() -> tuple[str, float]:
    """Generate a fresh bearer token and register its expiration.

    The token is a 256-bit URL-safe random string, so brute force is not
    a realistic attack vector. The TTL is fixed (not sliding) — operators
    must re-login every :data:`TOKEN_TTL_SECONDS` seconds.

    Return:
        token_and_expiry(tuple[str, float]): The bearer token and the
        unix timestamp at which it stops being valid.
    """
    token = secrets.token_urlsafe(32)
    now = time.time()
    expires_at = now + TOKEN_TTL_SECONDS
    with _lock:
        _prune_locked(now)
        _tokens[token] = expires_at
    return token, expires_at


def validate_token(token: str) -> bool:
    """Return True when the bearer token is registered and not expired.

    Args:
        token(str): The candidate bearer token.

    Return:
        valid(bool): True only when the token exists and the recorded
        expiry timestamp is still in the future.
    """
    if not token:
        return False
    now = time.time()
    with _lock:
        _prune_locked(now)
        expires_at = _tokens.get(token)
        if expires_at is None:
            return False
        return expires_at > now


def revoke_token(token: str) -> None:
    """Drop the token from the registry. No-op when it isn't there."""
    if not token:
        return
    with _lock:
        _tokens.pop(token, None)


def revoke_all_tokens() -> None:
    """Clear every issued bearer token. Used by tests and admin password rotations."""
    with _lock:
        _tokens.clear()


def _prune_locked(now: float) -> None:
    """Drop expired entries. Caller must hold ``_lock``."""
    expired = [token for token, exp in _tokens.items() if exp <= now]
    for token in expired:
        _tokens.pop(token, None)
