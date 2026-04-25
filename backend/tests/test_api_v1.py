from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import upload_file


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
