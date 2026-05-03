from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from oryups.services import cache
from tests.conftest import upload_file


def _login_and_get_bearer(client: TestClient) -> str:
    response = client.post(
        "/api/v1/admin/login",
        json={"password": "test-admin-secret"},
    )
    assert response.status_code == 200
    return response.json()["data"]["token"]


def test_clearcache_returns_envelope(client: TestClient) -> None:
    response = client.get(
        "/api/v1/clearcache",
        headers={"x-admin-token": "test-admin-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "Cache cleared",
        "data": None,
    }


def test_metadata_endpoint_returns_uploaded_metadata(client: TestClient) -> None:
    content = b"metadata content"
    fileid, _ = upload_file(client, "sample.txt", content)

    response = client.get(f"/api/v1/{fileid}/sample.txt")

    assert response.status_code == 200

    payload = response.json()
    data = payload["data"]

    assert payload["status"] == 200
    assert payload["message"] == "OK"
    assert data["id"] == fileid
    assert data["name"] == "sample.txt"
    assert data["mimeType"] == "text/plain"
    assert data["size"] == len(content)
    assert data["hidden"] is False
    assert isinstance(data["created_at"], int | float)
    assert data["delete_after"] == 3600.0
    assert "delete" not in data


def test_metadata_missing_returns_envelope_for_browser(client: TestClient) -> None:
    response = client.get(
        "/api/v1/abc123/missing.txt",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "status": 404,
        "message": "Not Found!",
        "data": None,
    }


def test_metadata_missing_returns_plain_text_for_curl(client: TestClient) -> None:
    response = client.get(
        "/api/v1/abc123/missing.txt",
        headers={"user-agent": "curl/8.0.1"},
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "404: Not Found!"


class TestPatchExpiry:
    """PATCH /api/v1/{fileid}/{filename} updates delete_after under admin auth."""

    def test_patch_extends_retention(
        self,
        client: TestClient,
        test_config: dict[str, Any],
    ) -> None:
        fileid, _ = upload_file(client, "extend.txt", b"payload")
        bearer = _login_and_get_bearer(client)

        response = client.patch(
            f"/api/v1/{fileid}/extend.txt",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"delete_after": 86400},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == 200
        assert body["message"] == "Updated"
        assert body["data"]["delete_after"] == 86400.0
        assert "delete" not in body["data"]
        assert response.headers.get("cache-control") == "no-store"
        assert response.headers.get("vary") == "Authorization"

        on_disk = json.loads(
            (Path(test_config["local"]["root"]) / fileid / "extend.txt.metadata").read_text()
        )
        assert on_disk["delete_after"] == 86400.0
        # Owner key must survive the rewrite.
        assert on_disk["delete"]

    def test_patch_never_expires_sentinel(
        self,
        client: TestClient,
        test_config: dict[str, Any],
    ) -> None:
        fileid, _ = upload_file(client, "pin.txt", b"pin")
        bearer = _login_and_get_bearer(client)

        response = client.patch(
            f"/api/v1/{fileid}/pin.txt",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"delete_after": -1},
        )

        assert response.status_code == 200
        assert response.json()["data"]["delete_after"] == -1.0

    def test_patch_invalidates_cache(
        self,
        client: TestClient,
        test_config: dict[str, Any],
    ) -> None:
        fileid, _ = upload_file(client, "cached.txt", b"cached")

        # Warm the cache.
        first = client.get(f"/api/v1/{fileid}/cached.txt")
        assert first.status_code == 200
        assert first.json()["data"]["delete_after"] == 3600.0

        bearer = _login_and_get_bearer(client)
        client.patch(
            f"/api/v1/{fileid}/cached.txt",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"delete_after": 60},
        )

        again = client.get(f"/api/v1/{fileid}/cached.txt")
        assert again.json()["data"]["delete_after"] == 60.0

    def test_patch_rejects_below_sentinel(self, client: TestClient) -> None:
        fileid, _ = upload_file(client, "validate.txt", b"x")
        bearer = _login_and_get_bearer(client)

        response = client.patch(
            f"/api/v1/{fileid}/validate.txt",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"delete_after": -2},
        )

        assert response.status_code == 422
        assert response.json()["status"] == 422

    def test_patch_rejects_non_finite(self, client: TestClient) -> None:
        fileid, _ = upload_file(client, "validate2.txt", b"x")
        bearer = _login_and_get_bearer(client)

        # Standard JSON cannot encode NaN; send the raw token to exercise
        # Pydantic's allow_inf_nan=False check via lax JSON parsing.
        response = client.patch(
            f"/api/v1/{fileid}/validate2.txt",
            headers={
                "Authorization": f"Bearer {bearer}",
                "Content-Type": "application/json",
            },
            content=b'{"delete_after": NaN}',
        )

        assert response.status_code == 422

    def test_patch_rejects_wrong_type(self, client: TestClient) -> None:
        fileid, _ = upload_file(client, "validate3.txt", b"x")
        bearer = _login_and_get_bearer(client)

        response = client.patch(
            f"/api/v1/{fileid}/validate3.txt",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"delete_after": "abc"},
        )

        assert response.status_code == 422

    def test_patch_requires_bearer(self, client: TestClient) -> None:
        fileid, _ = upload_file(client, "no_bearer.txt", b"x")

        response = client.patch(
            f"/api/v1/{fileid}/no_bearer.txt",
            json={"delete_after": 100},
        )

        assert response.status_code == 401
        assert response.json()["status"] == 401

    def test_patch_rejects_owner_key_alone(self, client: TestClient) -> None:
        upload = client.put("/owner_only.txt", content=b"x")
        owner_key = upload.headers["X-Owner-Key"]
        fileid = upload.text.rstrip("/").split("/")[-2]

        response = client.patch(
            f"/api/v1/{fileid}/owner_only.txt",
            headers={"X-Owner-Key": owner_key},
            json={"delete_after": 100},
        )

        # Owner key must NOT be accepted on PATCH; only admin bearer.
        assert response.status_code == 401

    def test_patch_404_when_file_missing(self, client: TestClient) -> None:
        bearer = _login_and_get_bearer(client)

        response = client.patch(
            "/api/v1/zzzzzz/missing.txt",
            headers={"Authorization": f"Bearer {bearer}"},
            json={"delete_after": 100},
        )

        assert response.status_code == 404
