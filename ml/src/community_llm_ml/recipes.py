from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

HEX64 = r"^[0-9a-f]{64}$"
MUTABLE_REFS = {"", "main", "master", "latest", "head"}


class RecipeError(ValueError):
    """Raised when a recipe or manifest is invalid."""


class BaseModelSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    revision: str = Field(min_length=1)

    @model_validator(mode="after")
    def _pin_revision(self) -> BaseModelSpec:
        if self.revision.lower() in MUTABLE_REFS:
            raise ValueError("base model revision must be an immutable commit")
        return self


class DatasetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train_uri: str = Field(min_length=1)
    train_sha256: str = Field(pattern=HEX64)
    validation_uri: str | None = None
    validation_sha256: str | None = Field(default=None, pattern=HEX64)
    license: str = Field(min_length=1)

    @model_validator(mode="after")
    def _validation_pair(self) -> DatasetSpec:
        if (self.validation_uri is None) != (self.validation_sha256 is None):
            raise ValueError("validation_uri and validation_sha256 must be provided together")
        return self


class EvalSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    cases_uri: str = Field(min_length=1)
    cases_sha256: str = Field(pattern=HEX64)
    rubric_uri: str | None = None
    rubric_sha256: str | None = Field(default=None, pattern=HEX64)

    @model_validator(mode="after")
    def _rubric_pair(self) -> EvalSpec:
        if (self.rubric_uri is None) != (self.rubric_sha256 is None):
            raise ValueError("rubric_uri and rubric_sha256 must be provided together")
        return self


class TrainingSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["qlora"]
    max_seq_length: int = Field(gt=0)
    max_steps: int = Field(gt=0)
    learning_rate: float = Field(gt=0)
    batch_size: int = Field(gt=0)
    gradient_accumulation_steps: int = Field(gt=0)
    seed: int
    validation_fraction: float = Field(default=0.05, ge=0, lt=1)


class LoraSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    r: int = Field(gt=0)
    alpha: int = Field(gt=0)
    dropout: float = Field(ge=0, lt=1)


class OutputSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    adapter_name: str = Field(min_length=1)
    save_steps: int = Field(gt=0)


class Recipe(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    name: str = Field(min_length=1)
    base_model: BaseModelSpec
    dataset: DatasetSpec
    eval: EvalSpec
    training: TrainingSpec
    lora: LoraSpec
    output: OutputSpec
    visibility: Literal["public", "private"] = "public"
    license: str = Field(min_length=1)


class BaseModelLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    revision: str


class DatasetLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train_uri: str
    train_sha256: str = Field(pattern=HEX64)
    validation_uri: str | None = None
    validation_sha256: str | None = Field(default=None, pattern=HEX64)


class EvalLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    cases_uri: str
    cases_sha256: str = Field(pattern=HEX64)


class ManifestLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1]
    recipe_sha256: str = Field(pattern=HEX64)
    base_model: BaseModelLock
    dataset: DatasetLock
    eval: EvalLock
    runner_version: str = Field(min_length=1)
    image_digest: str = Field(min_length=1)
    licenses: dict[str, str]
    created_at: str


class EvalVersionLock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    version: str
    cases_sha256: str = Field(pattern=HEX64)
    rubric_sha256: str | None = Field(default=None, pattern=HEX64)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_recipe(path: Path) -> Recipe:
    return Recipe.model_validate(yaml.safe_load(path.read_text()))


def load_manifest(path: Path) -> ManifestLock:
    return ManifestLock.model_validate(yaml.safe_load(path.read_text()))


def load_eval_lock(path: Path) -> EvalVersionLock:
    return EvalVersionLock.model_validate(yaml.safe_load(path.read_text()))


def validate_manifest(
    recipe: Recipe,
    manifest: ManifestLock,
    recipe_path: Path,
) -> None:
    digest = sha256_file(recipe_path)
    if digest != manifest.recipe_sha256:
        raise RecipeError(f"manifest recipe_sha256 is {manifest.recipe_sha256}, expected {digest}")

    if recipe.base_model.id != manifest.base_model.id:
        raise RecipeError("base model id does not match the manifest")
    if recipe.base_model.revision != manifest.base_model.revision:
        raise RecipeError("base model revision does not match the manifest")

    if recipe.dataset.train_uri != manifest.dataset.train_uri:
        raise RecipeError("dataset train_uri does not match the manifest")
    if recipe.dataset.train_sha256 != manifest.dataset.train_sha256:
        raise RecipeError("dataset train_sha256 does not match the manifest")
    if recipe.dataset.validation_uri != manifest.dataset.validation_uri:
        raise RecipeError("dataset validation_uri does not match the manifest")
    if recipe.dataset.validation_sha256 != manifest.dataset.validation_sha256:
        raise RecipeError("dataset validation_sha256 does not match the manifest")

    if (
        recipe.eval.id != manifest.eval.id
        or recipe.eval.version != manifest.eval.version
        or recipe.eval.cases_uri != manifest.eval.cases_uri
        or recipe.eval.cases_sha256 != manifest.eval.cases_sha256
    ):
        raise RecipeError("eval metadata does not match the manifest")

    for key in ("base_model", "dataset", "eval"):
        if not manifest.licenses.get(key):
            raise RecipeError(f"manifest is missing the {key} license")


def validate_local_assets(recipe: Recipe, root: Path) -> list[str]:
    errors: list[str] = []

    def check(uri: str | None, expected: str | None, label: str) -> None:
        if not uri or not expected:
            return
        if "://" in uri:
            return
        path = Path(uri)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            errors.append(f"{label}: missing file {path}")
            return
        actual = sha256_file(path)
        if actual != expected:
            errors.append(f"{label}: sha256 {actual} does not match {expected}")

    check(recipe.dataset.train_uri, recipe.dataset.train_sha256, "dataset.train")
    check(recipe.dataset.validation_uri, recipe.dataset.validation_sha256, "dataset.validation")
    check(recipe.eval.cases_uri, recipe.eval.cases_sha256, "eval.cases")
    check(recipe.eval.rubric_uri, recipe.eval.rubric_sha256, "eval.rubric")
    return errors


def recipe_schema_json() -> str:
    return json.dumps(Recipe.model_json_schema(), indent=2, sort_keys=True) + "\n"


def write_recipe_schema(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(recipe_schema_json())


def load_any_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text())
    if not isinstance(value, dict):
        raise RecipeError(f"{path}: expected a YAML mapping")
    return value
