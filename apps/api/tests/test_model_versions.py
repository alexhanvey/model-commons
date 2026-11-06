from __future__ import annotations

from fastapi.testclient import TestClient

RECIPE_REF = {
    "repository": "model-commons/recipes",
    "commit": "a" * 40,
    "path": "recipes/granite-4.1-3b/issue-tracker/v3",
    "manifest_sha256": "b" * 64,
}


def _payload(
    *,
    name: str = "granite-issue-tracker",
    version: str = "v3",
    primary: float = 0.76,
    baseline: float = 0.70,
    regression: float = 0.0,
    safety: bool = True,
) -> dict:
    return {
        "name": name,
        "version": version,
        "base_model": "ibm-granite/granite-4.1-3b",
        "base_revision": "c" * 40,
        "recipe_ref": RECIPE_REF,
        "adapter_uri": "s3://models/granite-issue-tracker-v3/adapter",
        "adapter_sha256": "d" * 64,
        "metrics": {
            "primary_metric": primary,
            "baseline_metric": baseline,
            "general_regression": regression,
            "safety_pass": safety,
            "sample_size": 60,
        },
        "model_card": "# Model Card\n\nCandidate.",
    }


def test_create_and_release_passing_candidate(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/admin/model-versions",
        json=_payload(),
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201
    model = created.json()
    assert model["status"] == "candidate"
    assert model["recipe_ref"]["commit"] == "a" * 40

    released = signed_in_client.post(
        f"/v1/admin/model-versions/{model['id']}/release",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert released.status_code == 200
    assert released.json()["status"] == "released"
    assert released.json()["released_at"] is not None

    listed = signed_in_client.get("/v1/model-versions")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_release_gate_blocks_underperforming_candidate(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/admin/model-versions",
        json=_payload(name="failing", primary=0.683333, baseline=0.70),
        headers={"X-CSRF-Token": csrf_token},
    )
    assert created.status_code == 201
    model = created.json()

    released = signed_in_client.post(
        f"/v1/admin/model-versions/{model['id']}/release",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert released.status_code == 422
    reasons = released.json()["detail"]["reasons"]
    assert any("primary metric" in reason for reason in reasons)

    fetched = signed_in_client.get(f"/v1/model-versions/{model['id']}")
    assert fetched.json()["status"] == "candidate"


def test_release_gate_blocks_regression_and_safety(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/admin/model-versions",
        json=_payload(
            name="regressed",
            regression=0.03,
            safety=False,
        ),
        headers={"X-CSRF-Token": csrf_token},
    )
    model = created.json()

    released = signed_in_client.post(
        f"/v1/admin/model-versions/{model['id']}/release",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert released.status_code == 422
    reasons = released.json()["detail"]["reasons"]
    assert any("general regression" in reason for reason in reasons)
    assert any("safety" in reason for reason in reasons)


def test_reject_candidate(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    created = signed_in_client.post(
        "/v1/admin/model-versions",
        json=_payload(name="reject-me"),
        headers={"X-CSRF-Token": csrf_token},
    )
    model = created.json()

    rejected = signed_in_client.post(
        f"/v1/admin/model-versions/{model['id']}/reject",
        json={"reason": "not good enough"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["rejected_at"] is not None


def test_duplicate_model_version_is_rejected(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    payload = _payload(name="duplicate")
    first = signed_in_client.post(
        "/v1/admin/model-versions",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert first.status_code == 201

    second = signed_in_client.post(
        "/v1/admin/model-versions",
        json=payload,
        headers={"X-CSRF-Token": csrf_token},
    )
    assert second.status_code == 409


def test_mutable_refs_are_rejected(
    signed_in_client: TestClient,
    csrf_token: str,
) -> None:
    payload = _payload(name="mutable")
    payload["base_revision"] = "main"
    assert (
        signed_in_client.post(
            "/v1/admin/model-versions",
            json=payload,
            headers={"X-CSRF-Token": csrf_token},
        ).status_code
        == 422
    )

    payload = _payload(name="mutable-recipe")
    payload["recipe_ref"] = {**RECIPE_REF, "commit": "main"}
    assert (
        signed_in_client.post(
            "/v1/admin/model-versions",
            json=payload,
            headers={"X-CSRF-Token": csrf_token},
        ).status_code
        == 422
    )
