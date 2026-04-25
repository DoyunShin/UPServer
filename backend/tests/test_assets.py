from __future__ import annotations

from fastapi.testclient import TestClient


def test_existing_asset_served(client: TestClient) -> None:
    response = client.get("/assets/img/favicon.svg")

    assert response.status_code == 200
    assert "image/svg" in response.headers["content-type"]
    assert response.content


def test_missing_asset_returns_404(client: TestClient) -> None:
    response = client.get(
        "/assets/nonexistent.css",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]


def test_path_traversal_asset_returns_404(client: TestClient) -> None:
    response = client.get(
        "/assets/%2E%2E/config.json",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
