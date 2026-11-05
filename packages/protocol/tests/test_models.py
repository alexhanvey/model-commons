from community_llm_protocol import ErrorResponse, HealthResponse, MetaResponse


def test_health_model() -> None:
    model = HealthResponse(service="api")
    assert model.status == "ok"


def test_meta_model() -> None:
    model = MetaResponse(name="api", version="0.1.0", environment="local")
    assert model.environment == "local"


def test_error_model() -> None:
    model = ErrorResponse(error="bad_request", message="invalid")
    assert model.error == "bad_request"
