from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from community_llm_ml.recipes import (
    Recipe,
    RecipeError,
    load_manifest,
    load_recipe,
    recipe_schema_json,
    validate_local_assets,
    validate_manifest,
)
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[2]
RECIPE_PATH = (
    ROOT / "tuning" / "recipes" / "granite-4.1-3b" / "issue-tracker" / "v3" / "recipe.yaml"
)
MANIFEST_PATH = RECIPE_PATH.with_name("manifest.lock")


def test_recipe_loads_with_pinned_revision() -> None:
    recipe = load_recipe(RECIPE_PATH)

    assert recipe.name == "granite-issue-tracker-v3"
    assert recipe.base_model.revision != "main"
    assert recipe.visibility == "public"


def test_recipe_rejects_unknown_keys() -> None:
    data = yaml.safe_load(RECIPE_PATH.read_text())
    data["unexpected"] = True

    with pytest.raises(ValidationError):
        Recipe.model_validate(data)


def test_recipe_rejects_mutable_revision() -> None:
    data = yaml.safe_load(RECIPE_PATH.read_text())
    data["base_model"]["revision"] = "main"

    with pytest.raises(ValidationError):
        Recipe.model_validate(data)


def test_manifest_and_local_assets_validate() -> None:
    recipe = load_recipe(RECIPE_PATH)
    manifest = load_manifest(MANIFEST_PATH)

    validate_manifest(recipe, manifest, RECIPE_PATH)
    assert validate_local_assets(recipe, ROOT) == []


def test_manifest_hash_mismatch_is_rejected() -> None:
    recipe = load_recipe(RECIPE_PATH)
    manifest = load_manifest(MANIFEST_PATH).model_copy(update={"recipe_sha256": "0" * 64})

    with pytest.raises(RecipeError):
        validate_manifest(recipe, manifest, RECIPE_PATH)


def test_schema_file_is_current() -> None:
    schema_path = ROOT / "tuning" / "schema" / "recipe.schema.json"
    assert schema_path.read_text() == recipe_schema_json()
