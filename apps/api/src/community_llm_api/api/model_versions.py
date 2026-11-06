from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from community_llm_protocol import (
    ModelVersionCreate,
    ModelVersionPublic,
    ModelVersionReject,
    ReleaseMetrics,
)
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from community_llm_api.audit import record_audit_event
from community_llm_api.dependencies import AdminCsrfContextDep, SessionContextDep, SessionDep
from community_llm_api.models.model_version import ModelVersion

router = APIRouter(prefix="/v1/model-versions", tags=["models"])
admin_router = APIRouter(prefix="/v1/admin/model-versions", tags=["admin"])

MUTABLE_REFS = {"", "main", "master", "latest", "head"}


def _public(model: ModelVersion) -> ModelVersionPublic:
    return ModelVersionPublic.model_validate(model)


def _release_reasons(model: ModelVersion) -> list[str]:
    reasons: list[str] = []
    metrics = ReleaseMetrics.model_validate(model.metrics)

    if metrics.primary_metric < metrics.baseline_metric + 0.05:
        reasons.append("primary metric must beat the baseline by at least 5 percentage points")
    if metrics.general_regression > 0.02:
        reasons.append("general regression exceeds 2 percentage points")
    if not metrics.safety_pass:
        reasons.append("safety gate failed")
    if not model.model_card.strip():
        reasons.append("model card is empty")
    if not model.adapter_uri.strip() or not model.adapter_sha256.strip():
        reasons.append("adapter URI and SHA-256 are required")
    if model.base_revision.lower() in MUTABLE_REFS:
        reasons.append("base model revision is mutable")

    ref = model.recipe_ref or {}
    if str(ref.get("commit", "")).lower() in MUTABLE_REFS:
        reasons.append("recipe commit is mutable")
    if not str(ref.get("manifest_sha256", "")).strip():
        reasons.append("recipe manifest SHA-256 is missing")
    return reasons


@admin_router.post("", response_model=ModelVersionPublic, status_code=status.HTTP_201_CREATED)
async def create_model_version(
    payload: ModelVersionCreate,
    context: AdminCsrfContextDep,
    db: SessionDep,
) -> ModelVersionPublic:
    existing = await db.scalar(
        select(ModelVersion).where(
            ModelVersion.name == payload.name,
            ModelVersion.version == payload.version,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="model version already exists")

    model = ModelVersion(
        name=payload.name,
        version=payload.version,
        base_model=payload.base_model,
        base_revision=payload.base_revision,
        recipe_ref=payload.recipe_ref.model_dump(),
        status="candidate",
        adapter_uri=payload.adapter_uri,
        adapter_sha256=payload.adapter_sha256,
        metrics=payload.metrics.model_dump(),
        model_card=payload.model_card,
        created_by_user_id=context.user.id,
    )
    db.add(model)
    await db.flush()
    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="model_version.create",
        target_type="model_version",
        target_id=model.id,
        data={"name": model.name, "version": model.version},
    )
    await db.commit()
    await db.refresh(model)
    return _public(model)


@router.get("", response_model=list[ModelVersionPublic])
async def list_model_versions(
    context: SessionContextDep,
    db: SessionDep,
) -> list[ModelVersionPublic]:
    query = select(ModelVersion).order_by(ModelVersion.created_at.desc())
    if not context.user.is_admin:
        query = query.where(ModelVersion.status == "released")
    result = await db.execute(query)
    return [_public(model) for model in result.scalars()]


@router.get("/{model_id}", response_model=ModelVersionPublic)
async def get_model_version(
    model_id: UUID,
    context: SessionContextDep,
    db: SessionDep,
) -> ModelVersionPublic:
    model = await db.get(ModelVersion, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model version not found")
    if model.status != "released" and not context.user.is_admin:
        raise HTTPException(status_code=404, detail="model version not found")
    return _public(model)


@admin_router.post("/{model_id}/release", response_model=ModelVersionPublic)
async def release_model_version(
    model_id: UUID,
    context: AdminCsrfContextDep,
    db: SessionDep,
) -> ModelVersionPublic:
    model = await db.get(ModelVersion, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model version not found")
    if model.status != "candidate":
        raise HTTPException(status_code=409, detail=f"model version is {model.status}")

    reasons = _release_reasons(model)
    if reasons:
        raise HTTPException(status_code=422, detail={"reasons": reasons})

    model.status = "released"
    model.released_at = datetime.now(UTC)
    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="model_version.release",
        target_type="model_version",
        target_id=model.id,
        data={"name": model.name, "version": model.version},
    )
    await db.commit()
    await db.refresh(model)
    return _public(model)


@admin_router.post("/{model_id}/reject", response_model=ModelVersionPublic)
async def reject_model_version(
    model_id: UUID,
    payload: ModelVersionReject,
    context: AdminCsrfContextDep,
    db: SessionDep,
) -> ModelVersionPublic:
    model = await db.get(ModelVersion, model_id)
    if model is None:
        raise HTTPException(status_code=404, detail="model version not found")
    if model.status != "candidate":
        raise HTTPException(status_code=409, detail=f"model version is {model.status}")

    model.status = "rejected"
    model.rejected_at = datetime.now(UTC)
    await record_audit_event(
        db,
        actor_user_id=context.user.id,
        action="model_version.reject",
        target_type="model_version",
        target_id=model.id,
        data={"name": model.name, "version": model.version, "reason": payload.reason},
    )
    await db.commit()
    await db.refresh(model)
    return _public(model)
