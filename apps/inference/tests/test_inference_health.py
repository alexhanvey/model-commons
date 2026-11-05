from community_llm_inference.main import app
from fastapi.testclient import TestClient


def test_healthz() -> None:
    response = TestClient(app).get("/healthz")
    assert response.status_code == 200
    assert response.json()["service"] == "community-llm-inference"


def test_models() -> None:
    response = TestClient(app).get("/v1/models")
    assert response.status_code == 200
    assert response.json() == {"data": []}
