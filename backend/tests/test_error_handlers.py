from __future__ import annotations

from fastapi.testclient import TestClient


def test_error_handler_returns_plain_text_for_curl(client: TestClient) -> None:
    response = client.get(
        "/missing/path",
        headers={"user-agent": "curl/8.0.1"},
    )

    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text == "404: Not Found!"


def test_error_handler_returns_envelope_for_api_path(client: TestClient) -> None:
    response = client.get(
        "/api/does-not-exist",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "status": 404,
        "message": "Not Found!",
        "data": None,
    }


def test_error_handler_returns_html_for_browser(client: TestClient) -> None:
    response = client.get(
        "/missing/path",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "404" in response.text
    assert "File not found" in response.text


def test_error_handler_renders_page_not_found_for_unknown_route(
    client: TestClient,
) -> None:
    response = client.get(
        "/no-such-page",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "Page not found" in response.text
