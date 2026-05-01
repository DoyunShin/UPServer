from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from tests.conftest import upload_file


def test_put_upload_returns_raw_share_url_and_stores_file(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    content = b"uploaded bytes"
    fileid, share_url = upload_file(client, "upload.txt", content)

    assert share_url == f"https://upload.example.test/{fileid}/upload.txt"
    assert Path(test_config["local"]["root"], fileid, "upload.txt").read_bytes() == content


def test_put_rejects_filename_containing_slash(client: TestClient) -> None:
    response = client.put("/nested/file.txt", content=b"nope")

    assert response.status_code == 400
    assert "text/html" in response.headers["content-type"]
    assert "Invalid path" in response.text


def test_put_rejects_dotfile(client: TestClient) -> None:
    response = client.put("/.secret", content=b"nope")

    assert response.status_code == 400
    assert "text/html" in response.headers["content-type"]
    assert "Invalid path" in response.text


def test_direct_get_returns_uploaded_bytes(client: TestClient) -> None:
    content = b"download me"
    fileid, _ = upload_file(client, "download.txt", content)

    response = client.get(f"/get/{fileid}/download.txt")

    assert response.status_code == 200
    assert response.content == content
    assert response.headers["content-type"].startswith("text/plain")


def test_direct_get_missing_returns_html_404(client: TestClient) -> None:
    response = client.get(
        "/get/abc123/missing.txt",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "404" in response.text
    assert "not found" in response.text.lower()


def test_share_page_browser_returns_index_html(client: TestClient) -> None:
    fileid, _ = upload_file(client, "share.txt", b"share page")

    response = client.get(
        f"/{fileid}/share.txt",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"<html" in response.content.lower()


def test_share_page_curl_streams_file_bytes(client: TestClient) -> None:
    content = b"curl bytes"
    fileid, _ = upload_file(client, "curl.txt", content)

    response = client.get(
        f"/{fileid}/curl.txt",
        headers={"user-agent": "curl/8.0.1"},
    )

    assert response.status_code == 200
    assert response.content == content


def test_share_page_wrong_fileid_length_returns_html_404(client: TestClient) -> None:
    response = client.get(
        "/abc12/file.txt",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "404" in response.text
    assert "not found" in response.text.lower()


def test_share_page_missing_valid_length_id_returns_html_404(client: TestClient) -> None:
    response = client.get(
        "/abc123/file.txt",
        headers={"user-agent": "Mozilla/5.0"},
    )

    assert response.status_code == 404
    assert "text/html" in response.headers["content-type"]
    assert "404" in response.text
    assert "not found" in response.text.lower()
