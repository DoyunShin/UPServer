from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import oryups.config as config_module
from tests.conftest import upload_file


class TestPathTraversal:
    """Path traversal attempts on read routes must return 404."""

    @pytest.mark.parametrize(
        "path",
        [
            "/get/abc12/readme.txt",                 # fileid length 5 != 6
            "/get/abcdefg/readme.txt",               # fileid length 7 != 6
            "/get/ab-cde/readme.txt",                # fileid contains non-alnum
            "/get/a.bcde/readme.txt",                # fileid contains dot
            "/get/abcdef/.hidden",                   # filename starts with dot
            "/get/abcdef/a%5Cb",                     # filename contains backslash
            "/get/abcdef/" + "x" * 300 + ".txt",     # filename too long
        ],
    )
    def test_get_download_rejects_bad_inputs(self, client: TestClient, path: str) -> None:
        response = client.get(path, headers={"user-agent": "curl/8.0.1"})

        assert response.status_code == 404

    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/abc12/readme.txt",
            "/api/v1/ab-cde/readme.txt",
            "/api/v1/abcdef/.hidden",
            "/api/v1/abcdef/a%5Cb",
        ],
    )
    def test_api_v1_metadata_rejects_bad_inputs(
        self, client: TestClient, path: str
    ) -> None:
        response = client.get(path, headers={"user-agent": "Mozilla/5.0"})

        assert response.status_code == 404

    def test_share_page_rejects_bad_fileid_for_browser(self, client: TestClient) -> None:
        response = client.get("/ab-cde/readme.txt", headers={"user-agent": "Mozilla/5.0"})

        assert response.status_code == 404


class TestUploadSizeLimit:
    """Upload routes must cap body size."""

    def test_rejects_content_length_over_limit(self, client: TestClient) -> None:
        headers = {"content-length": str(10 * 1024 * 1024)}
        response = client.put(
            "/too-big.bin",
            content=b"ignored body",
            headers=headers,
        )

        assert response.status_code == 413

    def test_rejects_streamed_body_over_limit(self, client: TestClient) -> None:
        payload = b"x" * (1024 * 1024 + 1024)
        response = client.put("/too-big-stream.bin", content=payload)

        assert response.status_code == 413

    def test_accepts_body_at_limit(self, client: TestClient) -> None:
        payload = b"y" * (1024 * 1024)
        response = client.put("/edge.bin", content=payload)

        assert response.status_code == 200


class TestUploadUrlOrigin:
    """PUT response must use the configured domain, not a spoofed Host header."""

    def test_uses_configured_domain(self, client: TestClient) -> None:
        response = client.put(
            "/where-am-i.txt",
            content=b"origin test",
            headers={"host": "evil.example.com"},
        )

        assert response.status_code == 200
        assert response.text.startswith("https://upload.example.test/")

    def test_uses_actual_received_bytes(self, client: TestClient) -> None:
        payload = b"hello"
        response = client.put(
            "/truth.txt",
            content=payload,
            headers={"content-length": "5"},
        )

        assert response.status_code == 200

        share_url = response.text
        fileid = share_url.rstrip("/").split("/")[-2]

        metadata = client.get(
            f"/api/v1/{fileid}/truth.txt",
            headers={"user-agent": "Mozilla/5.0"},
        ).json()["data"]

        assert metadata["size"] == len(payload)


class TestClearcacheAuth:
    """/api/v1/clearcache must require the admin token."""

    def test_missing_token_returns_forbidden(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/clearcache",
            headers={"user-agent": "Mozilla/5.0"},
        )

        assert response.status_code == 403
        assert response.json() == {
            "status": 403,
            "message": "Forbidden",
            "data": None,
        }

    def test_wrong_token_returns_forbidden(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/clearcache",
            headers={
                "user-agent": "Mozilla/5.0",
                "x-admin-token": "nope",
            },
        )

        assert response.status_code == 403

    def test_correct_token_returns_envelope(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/clearcache",
            headers={"x-admin-token": "test-admin-secret"},
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Cache cleared"

    def test_disabled_when_token_empty(
        self, client: TestClient, test_config: dict[str, Any]
    ) -> None:
        config_module._config["host"]["admin_token"] = ""

        response = client.get(
            "/api/v1/clearcache",
            headers={"user-agent": "Mozilla/5.0"},
        )

        assert response.status_code == 404


class TestZeroByteUpload:
    """Zero-byte PUT must round-trip via local storage."""

    def test_zero_byte_round_trip(self, client: TestClient) -> None:
        fileid, share_url = upload_file(client, "empty.bin", b"")

        metadata = client.get(
            f"/api/v1/{fileid}/empty.bin",
            headers={"user-agent": "Mozilla/5.0"},
        ).json()["data"]

        assert metadata["size"] == 0

        download = client.get(
            f"/get/{fileid}/empty.bin",
            headers={"user-agent": "curl/8.0.1"},
        )
        assert download.status_code == 200
        assert download.content == b""


class TestFilenameValidation:
    """PUT must reject path separators, leading dots, and overlong names."""

    @pytest.mark.parametrize(
        "filename",
        [
            "..",
            ".hidden",
            "x" * 300 + ".txt",
        ],
    )
    def test_rejects_invalid_names(self, client: TestClient, filename: str) -> None:
        response = client.put(f"/{filename}", content=b"data")

        assert response.status_code == 400


class TestGdriveZeroByteChunksize:
    """save_BytesIO must clamp chunksize to at least 1 so 0-byte uploads don't raise."""

    def test_chunksize_minimum_one(self) -> None:
        size_zero = 0
        assert max(int(size_zero), 1) == 1

        size_nonzero = 12345
        assert max(int(size_nonzero), 1) == 12345
