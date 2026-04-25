import time

from oryups.filesystem import Metadata


def is_expired(metadata: Metadata, delete_rule: dict) -> bool:
    """Return True when the metadata has passed its retention window.

    Args:
        metadata(Metadata): Loaded metadata object.
        delete_rule(dict): The ``config["delete"]`` block.

    Return:
        expired(bool): True if retention is enabled, ``delete_after`` is
        positive, and ``created_at + delete_after <= now``.
    """
    if not delete_rule.get("enabled", False):
        return False
    after = float(getattr(metadata, "delete_after", -1) or -1)
    if after <= 0:
        return False
    created = float(getattr(metadata, "created_at", 0) or 0)
    return (created + after) <= time.time()
