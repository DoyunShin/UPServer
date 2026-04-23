from __future__ import annotations

import json
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import oryups.config as config_module
import oryups.main as main_module
from oryups.main import app
from oryups.services import cache


@pytest.fixture()
def test_config(tmp_path: Path) -> Generator[dict[str, Any], None, None]:
    """Load an isolated config and storage root for a single test."""
    example_path = config_module.BASE_DIR / "config.example.json"
    config = json.loads(example_path.read_text(encoding="utf-8"))

    storage_root = tmp_path / "storage"
    config["storage"] = "local"
    config["local"]["root"] = str(storage_root.resolve())
    config["host"]["domain"] = "https://upload.example.test/"
    config["host"]["proxy"] = False
    config["host"]["cdn"]["enabled"] = False
    config["host"]["cachetime"] = 600
    config["folderidlength"] = 6
    config["general"] = {
        "name": "Test Upload",
        "brand": "UPServer Tests",
        "info": "FastAPI migration verification",
        "icon": "https://example.test/favicon.ico",
        "contact": "https://example.test/contact",
        "webinfo": [["Docs", ["API", "https://example.test/api"]]],
    }

    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    config_module.load_config(path=config_path)
    cache._cache.clear()

    try:
        yield config
    finally:
        cache._cache.clear()
        config_module._config = {}
        config_module._storage = None
        config_module._config_path = None


@pytest.fixture()
def client(
    monkeypatch: pytest.MonkeyPatch,
    test_config: dict[str, Any],
) -> Generator[TestClient, None, None]:
    """Create a TestClient without letting lifespan reload the real config."""
    def _noop_load_config(path: Path | None = None) -> dict[str, Any]:
        return config_module.get_config()

    monkeypatch.setattr(config_module, "load_config", _noop_load_config)
    monkeypatch.setattr(main_module, "load_config", _noop_load_config)

    with TestClient(app, backend_options={"use_uvloop": True}) as test_client:
        yield test_client


def upload_file(
    client: TestClient,
    filename: str = "hello.txt",
    content: bytes = b"hello from pytest",
) -> tuple[str, str]:
    """Upload bytes and return the generated file id and share URL."""
    response = client.put(f"/{filename}", content=content)

    assert response.status_code == 200

    share_url = response.text
    parts = share_url.rstrip("/").split("/")
    return parts[-2], share_url
