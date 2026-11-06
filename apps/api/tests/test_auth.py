from __future__ import annotations

from fastapi.testclient import TestClient


def _login(client: TestClient) -> str:
    response = client.get("/v1/auth/github/login", follow_redirects=False)
    assert response.status_code == 302
    state = response.cookies.get("community_oauth_state")
    assert state
    return state


def _callback(client: TestClient, state: str, code: str = "good-code"):
    return client.get(
        "/v1/auth/github/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


def test_login_redirects_to_github(client: TestClient) -> None:
    response = client.get("/v1/auth/github/login", follow_redirects=False)

    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("https://github.com/login/oauth/authorize?")
    assert "state=" in location
    assert response.cookies.get("community_oauth_state")


def test_callback_creates_session(client: TestClient) -> None:
    state = _login(client)
    response = _callback(client, state)

    assert response.status_code == 302
    assert response.headers["location"] == "http://localhost:3000/"
    assert response.cookies.get("community_session")

    me = client.get("/v1/me")
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["login"] == "alexhanvey"
    assert body["user"]["email"] == "alex@example.com"
    assert body["user"]["is_admin"] is True
    assert body["csrf_token"]


def test_callback_rejects_bad_state(client: TestClient) -> None:
    _login(client)

    response = _callback(client, "wrong-state")

    assert response.status_code == 400


def test_callback_rejects_bad_code(client: TestClient) -> None:
    state = _login(client)

    response = _callback(client, state, code="bad-code")

    assert response.status_code == 502


def test_me_requires_session(client: TestClient) -> None:
    assert client.get("/v1/me").status_code == 401


def test_logout_revokes_session_and_requires_csrf(client: TestClient) -> None:
    state = _login(client)
    assert _callback(client, state).status_code == 302
    csrf = client.get("/v1/me").json()["csrf_token"]

    assert client.post("/v1/auth/logout").status_code == 403

    response = client.post("/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 204
    assert client.get("/v1/me").status_code == 401
