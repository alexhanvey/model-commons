import httpx
from community_llm_sdk import CommunityLLMClient


def test_health() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/healthz"
        return httpx.Response(200, json={"status": "ok", "service": "api"})

    client = CommunityLLMClient("http://test")
    client._client = httpx.Client(base_url="http://test", transport=httpx.MockTransport(handler))
    result = client.health()
    assert result.status == "ok"
    assert result.service == "api"
