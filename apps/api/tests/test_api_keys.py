from __future__ import annotations

import asyncio

import pytest
from community_llm_api.dependencies import Principal, require_scope
from community_llm_api.models.user import User
from community_llm_protocol import Scope
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_create_list_use_and_revoke(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/api-keys",
        json={"name": "agent", "scopes": ["inference:write", "jobs:read"]},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201

    body = created.json()
    token = body["token"]
    api_key = body["api_key"]
    assert token.startswith("clm_")
    assert api_key["name"] == "agent"
    assert set(api_key["scopes"]) == {"inference:write", "jobs:read"}
    assert api_key["prefix"].startswith("clm_")

    listed = signed_in_client.get("/v1/api-keys")
    assert listed.status_code == 200
    keys = listed.json()
    assert len(keys) == 1
    assert "token" not in keys[0]

    me = signed_in_client.get(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me.status_code == 200
    assert me.json()["auth_method"] == "api_key"
    assert me.json()["csrf_token"] is None

    revoked = signed_in_client.delete(
        f"/v1/api-keys/{api_key['id']}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert revoked.status_code == 204

    rejected = signed_in_client.get(
        "/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rejected.status_code == 401


def test_create_requires_csrf(signed_in_client: TestClient) -> None:
    response = signed_in_client.post(
        "/v1/api-keys",
        json={"name": "agent", "scopes": ["inference:write"]},
    )
    assert response.status_code == 403


def test_unknown_scope_is_rejected(signed_in_client: TestClient, csrf_token: str) -> None:
    response = signed_in_client.post(
        "/v1/api-keys",
        json={"name": "agent", "scopes": ["not-a-scope"]},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert response.status_code == 422


def test_api_key_cannot_manage_api_keys(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/api-keys",
        json={"name": "agent", "scopes": ["inference:write"]},
        headers={"X-CSRF-Token": csrf_token},
    )
    token = created.json()["token"]

    signed_in_client.cookies.clear()
    response = signed_in_client.post(
        "/v1/api-keys",
        json={"name": "another", "scopes": ["inference:write"]},
        headers={"Authorization": f"Bearer {token}", "X-CSRF-Token": "unused"},
    )
    assert response.status_code == 401


def test_require_scope() -> None:
    user = User(github_id=1, login="tester")
    dependency = require_scope(Scope.JOBS_WRITE)

    session = Principal(user=user, auth_method="session", scopes=frozenset())
    assert asyncio.run(dependency(session)).user is user

    allowed = Principal(
        user=user,
        auth_method="api_key",
        scopes=frozenset({Scope.JOBS_WRITE.value}),
    )
    assert asyncio.run(dependency(allowed)).user is user

    denied = Principal(
        user=user,
        auth_method="api_key",
        scopes=frozenset({Scope.JOBS_READ.value}),
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(dependency(denied))
    assert exc.value.status_code == 403
