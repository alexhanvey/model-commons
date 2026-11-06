from __future__ import annotations

import shutil
from pathlib import Path

from validate_tuning import validate

ROOT = Path(__file__).resolve().parents[2]


def test_repo_tuning_validates() -> None:
    assert validate(ROOT) == []


def test_validator_detects_stale_schema(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "tuning", tmp_path / "tuning")
    data_dir = tmp_path / "spikes" / "issue_tracker" / "data"
    data_dir.mkdir(parents=True)
    shutil.copy(
        ROOT / "spikes" / "issue_tracker" / "data" / "issue_tracker_train_v2.jsonl",
        data_dir / "issue_tracker_train_v2.jsonl",
    )

    assert validate(tmp_path) == []

    (tmp_path / "tuning" / "schema" / "recipe.schema.json").write_text("{}")
    errors = validate(tmp_path)
    assert any("schema is stale" in error for error in errors)
