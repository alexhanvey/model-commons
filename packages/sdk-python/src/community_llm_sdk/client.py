from __future__ import annotations

import httpx
from community_llm_protocol import HealthResponse, MetaResponse


class CommunityLLMClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def health(self) -> HealthResponse:
        response = self._client.get("/healthz")
        response.raise_for_status()
        return HealthResponse.model_validate(response.json())

    def meta(self) -> MetaResponse:
        response = self._client.get("/v1/meta")
        response.raise_for_status()
        return MetaResponse.model_validate(response.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CommunityLLMClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
