import time

from oryups.filesystem import Metadata


NEVER_EXPIRES_SENTINEL: float = -1.0


def is_expired(metadata: Metadata, delete_rule: dict) -> bool:
    """Return True when the metadata has passed its retention window.

    Only ``delete_after == -1`` is treated as "never expires". Any other
    value (including ``0`` and negatives other than ``-1``) is interpreted
    as a retention window relative to ``created_at`` — non-positive values
    therefore mean the file is already past its window.

    Args:
        metadata(Metadata): Loaded metadata object.
        delete_rule(dict): The ``config["delete"]`` block.

    Return:
        expired(bool): True when retention is enabled, ``delete_after`` is
        not the never-sentinel, and ``created_at + delete_after <= now``.
    """
    if not delete_rule.get("enabled", False):
        return False
    after = float(getattr(metadata, "delete_after", NEVER_EXPIRES_SENTINEL) or NEVER_EXPIRES_SENTINEL)
    if after == NEVER_EXPIRES_SENTINEL:
        return False
    created = float(getattr(metadata, "created_at", 0) or 0)
    return (created + after) <= time.time()
