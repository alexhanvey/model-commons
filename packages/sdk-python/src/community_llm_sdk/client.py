from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

import httpx
from community_llm_protocol import (
    AdminGrantResponse,
    ApiKeyCreated,
    ApiKeyPublic,
    HealthResponse,
    JobKind,
    JobPublic,
    LedgerTransactionPublic,
    MeResponse,
    MetaResponse,
    PointsBalance,
    Scope,
    WorkerCreated,
    WorkerPublic,
)


class CommunityLLMClient:
    """Client for the control-plane API.

    Use ``api_key`` for bearer access, ``worker_token`` for worker heartbeats, and
    ``session_cookie`` plus ``csrf_token`` for management endpoints.
    """

    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        worker_token: str | None = None,
        session_cookie: str | None = None,
        csrf_token: str | None = None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.worker_token = worker_token
        self.session_cookie = session_cookie
        self.csrf_token = csrf_token

        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        elif worker_token:
            headers["Authorization"] = f"Bearer {worker_token}"
        if session_cookie:
            headers["Cookie"] = f"community_session={session_cookie}"

        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            headers=headers,
            transport=transport,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        mutation: bool = False,
    ) -> httpx.Response:
        headers: dict[str, str] = {}
        if mutation:
            if not self.csrf_token:
                raise ValueError("csrf_token is required for cookie-auth mutations")
            headers["X-CSRF-Token"] = self.csrf_token
        response = self._client.request(method, path, json=json, headers=headers)
        response.raise_for_status()
        return response

    def health(self) -> HealthResponse:
        return HealthResponse.model_validate(self._request("GET", "/healthz").json())

    def meta(self) -> MetaResponse:
        return MetaResponse.model_validate(self._request("GET", "/v1/meta").json())

    def me(self) -> MeResponse:
        return MeResponse.model_validate(self._request("GET", "/v1/me").json())

    def create_api_key(
        self,
        name: str,
        scopes: Sequence[Scope | str],
    ) -> ApiKeyCreated:
        payload = {
            "name": name,
            "scopes": [scope.value if isinstance(scope, Scope) else scope for scope in scopes],
        }
        response = self._request("POST", "/v1/api-keys", json=payload, mutation=True)
        return ApiKeyCreated.model_validate(response.json())

    def list_api_keys(self) -> list[ApiKeyPublic]:
        response = self._request("GET", "/v1/api-keys")
        return [ApiKeyPublic.model_validate(item) for item in response.json()]

    def revoke_api_key(self, key_id: UUID | str) -> None:
        self._request("DELETE", f"/v1/api-keys/{key_id}", mutation=True)

    def create_worker(self, name: str) -> WorkerCreated:
        response = self._request(
            "POST",
            "/v1/workers",
            json={"name": name},
            mutation=True,
        )
        return WorkerCreated.model_validate(response.json())

    def list_workers(self) -> list[WorkerPublic]:
        response = self._request("GET", "/v1/workers")
        return [WorkerPublic.model_validate(item) for item in response.json()]

    def approve_worker(self, worker_id: UUID | str) -> WorkerPublic:
        response = self._request("POST", f"/v1/workers/{worker_id}/approve", mutation=True)
        return WorkerPublic.model_validate(response.json())

    def revoke_worker(self, worker_id: UUID | str) -> None:
        self._request("DELETE", f"/v1/workers/{worker_id}", mutation=True)

    def worker_heartbeat(self) -> WorkerPublic:
        if not self.worker_token:
            raise ValueError("worker_token is required for heartbeats")
        response = self._client.post(
            "/v1/workers/heartbeat",
            headers={"Authorization": f"Bearer {self.worker_token}"},
        )
        response.raise_for_status()
        return WorkerPublic.model_validate(response.json())

    def create_job(
        self,
        kind: JobKind | str,
        spec: dict[str, Any] | None = None,
    ) -> JobPublic:
        kind_value = kind.value if isinstance(kind, JobKind) else kind
        response = self._request(
            "POST",
            "/v1/jobs",
            json={"kind": kind_value, "spec": spec or {}},
            mutation=True,
        )
        return JobPublic.model_validate(response.json())

    def list_jobs(self) -> list[JobPublic]:
        response = self._request("GET", "/v1/jobs")
        return [JobPublic.model_validate(item) for item in response.json()]

    def get_job(self, job_id: UUID | str) -> JobPublic:
        response = self._request("GET", f"/v1/jobs/{job_id}")
        return JobPublic.model_validate(response.json())

    def cancel_job(self, job_id: UUID | str) -> JobPublic:
        response = self._request("POST", f"/v1/jobs/{job_id}/cancel", mutation=True)
        return JobPublic.model_validate(response.json())

    def points_balance(self) -> PointsBalance:
        return PointsBalance.model_validate(self._request("GET", "/v1/points/balance").json())

    def points_transactions(self) -> list[LedgerTransactionPublic]:
        response = self._request("GET", "/v1/points/transactions")
        return [LedgerTransactionPublic.model_validate(item) for item in response.json()]

    def admin_grant(
        self,
        user_id: UUID | str,
        amount: int,
        reason: str,
        idempotency_key: str,
    ) -> AdminGrantResponse:
        response = self._request(
            "POST",
            "/v1/admin/grants",
            json={
                "user_id": str(user_id),
                "amount": amount,
                "reason": reason,
                "idempotency_key": idempotency_key,
            },
            mutation=True,
        )
        return AdminGrantResponse.model_validate(response.json())

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> CommunityLLMClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
