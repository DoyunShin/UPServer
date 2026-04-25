from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_get_root_serves_index_html(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<html" in response.content.lower()


def test_post_root_serves_index_html(client: TestClient) -> None:
    response = client.post("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<html" in response.content.lower()


def test_robots_txt_is_plain_text(client: TestClient) -> None:
    response = client.get("/robots.txt")

    assert response.status_code == 200
    assert response.text == "Disallow: /"
    assert response.headers["content-type"].startswith("text/plain")


def test_favicon_redirects_to_configured_icon(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    response = client.get("/favicon.ico", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == test_config["general"]["icon"]


def test_index_html_redirects_to_root(client: TestClient) -> None:
    response = client.get("/index.html", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/"
