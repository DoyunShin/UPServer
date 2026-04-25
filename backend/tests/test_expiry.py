from __future__ import annotations

import json
import string
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from oryups.config import get_config
from oryups.services import cache
from oryups.services.reaper import reap_once
from tests.conftest import upload_file


def _metadata_path(test_config: dict[str, Any], fileid: str, filename: str) -> Path:
    return Path(test_config["local"]["root"]) / fileid / f"{filename}.metadata"


def _expire_metadata(path: Path, fileid: str) -> None:
    """Rewrite the on-disk metadata so the file is retroactively expired."""
    data = json.loads(path.read_text())
    data["created_at"] = 0
    data["delete_after"] = 1
    path.write_text(json.dumps(data))
    cache.invalidate(fileid)


def test_upload_curl_hides_owner_key(client: TestClient) -> None:
    response = client.put(
        "/curlfile.txt",
        content=b"curl data",
        headers={"user-agent": "curl/8.0.1"},
    )

    assert response.status_code == 200
    assert "x-owner-key" not in {k.lower() for k in response.headers.keys()}


def test_upload_browser_returns_owner_key(client: TestClient) -> None:
    response = client.put(
        "/browserfile.txt",
        content=b"browser data",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 200
    owner_key = response.headers.get("X-Owner-Key")
    assert owner_key is not None
    assert len(owner_key) == 12
    allowed = set(string.ascii_letters + string.digits)
    assert set(owner_key).issubset(allowed)


def test_delete_requires_owner_key(client: TestClient) -> None:
    fileid, _ = upload_file(client, "tokill.txt", b"payload")

    response = client.delete(f"/{fileid}/tokill.txt")

    assert response.status_code == 403
    assert response.json() == {"status": 403, "message": "Forbidden", "data": None}


def test_delete_rejects_wrong_owner_key(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    fileid, _ = upload_file(client, "tokill2.txt", b"payload")

    response = client.delete(
        f"/{fileid}/tokill2.txt",
        headers={"X-Owner-Key": "00000000"},
    )

    assert response.status_code == 403
    file_path = Path(test_config["local"]["root"]) / fileid / "tokill2.txt"
    assert file_path.exists()


def test_delete_with_correct_owner_key_removes_file(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    put_response = client.put(
        "/deleteme.txt",
        content=b"bye",
        headers={"user-agent": "Mozilla/5.0"},
    )
    assert put_response.status_code == 200
    owner_key = put_response.headers["X-Owner-Key"]
    fileid = put_response.text.rstrip("/").split("/")[-2]

    delete_response = client.delete(
        f"/{fileid}/deleteme.txt",
        headers={"X-Owner-Key": owner_key},
    )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "status": 200,
        "message": "Deleted",
        "data": None,
    }
    assert not (Path(test_config["local"]["root"]) / fileid).exists()

    get_response = client.get(f"/get/{fileid}/deleteme.txt")
    assert get_response.status_code == 404


def test_lazy_expiry_returns_404_keeps_file_on_disk(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    fileid, _ = upload_file(client, "oldfile.txt", b"oldbytes")
    _expire_metadata(_metadata_path(test_config, fileid, "oldfile.txt"), fileid)

    response = client.get(f"/get/{fileid}/oldfile.txt")

    assert response.status_code == 404
    assert (Path(test_config["local"]["root"]) / fileid / "oldfile.txt").exists()


def test_lazy_expiry_api_v1_metadata_returns_404(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    fileid, _ = upload_file(client, "oldmeta.txt", b"oldbytes")
    _expire_metadata(_metadata_path(test_config, fileid, "oldmeta.txt"), fileid)

    response = client.get(f"/api/v1/{fileid}/oldmeta.txt")

    assert response.status_code == 404
    assert response.json()["status"] == 404


def test_retention_disabled_never_expires(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    get_config()["delete"]["enabled"] = False
    fileid, _ = upload_file(client, "keepme.txt", b"keep")
    _expire_metadata(_metadata_path(test_config, fileid, "keepme.txt"), fileid)

    response = client.get(f"/get/{fileid}/keepme.txt")

    assert response.status_code == 200
    assert response.content == b"keep"


def test_reap_once_removes_expired_when_permanently_true(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    get_config()["delete"]["permanently"] = True

    fileid, _ = upload_file(client, "reap.txt", b"reap me")
    _expire_metadata(_metadata_path(test_config, fileid, "reap.txt"), fileid)

    removed = reap_once()

    assert removed == 1
    assert not (Path(test_config["local"]["root"]) / fileid).exists()


def test_reap_once_noop_when_permanently_false(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    fileid, _ = upload_file(client, "keep2.txt", b"keep")
    _expire_metadata(_metadata_path(test_config, fileid, "keep2.txt"), fileid)

    removed = reap_once()

    assert removed == 0
    assert (Path(test_config["local"]["root"]) / fileid / "keep2.txt").exists()
