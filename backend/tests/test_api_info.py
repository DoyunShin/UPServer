from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def test_api_info_returns_general_config(
    client: TestClient,
    test_config: dict[str, Any],
) -> None:
    response = client.get("/api/info")

    assert response.status_code == 200
    assert response.json() == {
        "status": 200,
        "message": "OK",
        "data": test_config["general"],
    }
