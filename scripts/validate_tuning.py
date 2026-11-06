#!/usr/bin/env python3
"""Validate the tuning recipe tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from community_llm_ml.data.prepare_dataset import (
    ContaminationError,
    check_contamination,
    eval_prompt_keys,
    load_jsonl,
)
from community_llm_ml.recipes import (
    EvalSpec,
    EvalVersionLock,
    RecipeError,
    load_eval_lock,
    load_manifest,
    load_recipe,
    recipe_schema_json,
    validate_local_assets,
    validate_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def _validate_eval_lock(
    root: Path,
    recipe_eval: EvalSpec,
    errors: list[str],
) -> None:
    eval_dir = root / "tuning" / "evals" / recipe_eval.id / recipe_eval.version
    lock_path = eval_dir / "version.lock"
    if not lock_path.exists():
        errors.append(f"missing eval version lock: {lock_path}")
        return
    try:
        lock: EvalVersionLock = load_eval_lock(lock_path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{lock_path}: {exc}")
        return
    if lock.id != recipe_eval.id or lock.version != recipe_eval.version:
        errors.append(f"{lock_path}: id/version does not match the recipe")
    if lock.cases_sha256 != recipe_eval.cases_sha256:
        errors.append(f"{lock_path}: cases_sha256 does not match the recipe")
    if recipe_eval.rubric_sha256 and lock.rubric_sha256 != recipe_eval.rubric_sha256:
        errors.append(f"{lock_path}: rubric_sha256 does not match the recipe")


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    recipe_paths = sorted((root / "tuning" / "recipes").glob("**/recipe.yaml"))
    if not recipe_paths:
        errors.append("no tuning recipes found")

    for recipe_path in recipe_paths:
        try:
            recipe = load_recipe(recipe_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{recipe_path}: {exc}")
            continue

        manifest_path = recipe_path.with_name("manifest.lock")
        if not manifest_path.exists():
            errors.append(f"{recipe_path}: missing manifest.lock")
            continue
        try:
            manifest = load_manifest(manifest_path)
            validate_manifest(recipe, manifest, recipe_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{manifest_path}: {exc}")
            continue

        errors.extend(validate_local_assets(recipe, root))
        _validate_eval_lock(root, recipe.eval, errors)

        train_uri = recipe.dataset.train_uri
        if "://" not in train_uri:
            train_path = Path(train_uri)
            if not train_path.is_absolute():
                train_path = root / train_path
            if train_path.exists():
                try:
                    train_examples = load_jsonl(train_path)
                    eval_path = Path(recipe.eval.cases_uri)
                    if not eval_path.is_absolute():
                        eval_path = root / eval_path
                    check_contamination(train_examples, eval_prompt_keys(eval_path))
                except ContaminationError as exc:
                    errors.append(f"{recipe_path}: {exc}")
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{recipe_path}: contamination check failed: {exc}")

        if manifest.image_digest == "local-dev":
            print(
                f"warning: {manifest_path}: image_digest is local-dev; "
                "pin a real image before release",
                file=sys.stderr,
            )

    schema_path = root / "tuning" / "schema" / "recipe.schema.json"
    if not schema_path.exists():
        errors.append(f"missing schema: {schema_path}")
    elif schema_path.read_text() != recipe_schema_json():
        errors.append(f"{schema_path}: schema is stale; run --write-schema")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write-schema", action="store_true")
    args = parser.parse_args()

    if args.write_schema:
        path = args.root / "tuning" / "schema" / "recipe.schema.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(recipe_schema_json())
        print(f"wrote {path}")
        return 0

    try:
        errors = validate(args.root)
    except RecipeError as exc:
        errors = [str(exc)]

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    print("tuning validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
