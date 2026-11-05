from community_llm_api.main import app
from fastapi.testclient import TestClient


def test_healthz() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_readyz() -> None:
    response = TestClient(app).get("/readyz")
    assert response.status_code == 200
    assert response.json()["service"] == "community-llm-api"


def test_meta() -> None:
    response = TestClient(app).get("/v1/meta")
    assert response.status_code == 200
    assert response.json()["name"] == "community-llm-api"
