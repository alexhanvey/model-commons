#!/usr/bin/env python3
"""Prepare reproducible JSONL training data.

The pipeline validates records, normalizes text, removes exact and
prompt-normalized duplicates, scrubs common PII patterns, checks contamination
against an eval set, writes deterministic splits, and produces a manifest and
dataset card.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_ROLES = {"system", "user", "assistant", "tool"}
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE_RE = re.compile(r"\b(?:\+?\d[\d\s().-]{7,}\d)\b")
SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
WHITESPACE_RE = re.compile(r"\s+")


class DatasetError(ValueError):
    """Raised when training data fails validation."""


class ContaminationError(DatasetError):
    """Raised when training prompts overlap the eval set."""


@dataclass(frozen=True)
class SplitInfo:
    name: str
    path: str
    examples: int
    sha256: str


@dataclass(frozen=True)
class DatasetManifest:
    name: str
    version: str
    source: str
    license: str
    input_path: str
    input_sha256: str
    seed: int
    created_at: str
    processor_version: str
    splits: list[SplitInfo]
    eval_path: str | None
    eval_sha256: str | None
    deduplicated: int
    near_duplicates: int
    pii_replacements: int
    contamination_matches: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"{path}:{line_number}: invalid JSON") from exc
        if not isinstance(value, dict):
            raise DatasetError(f"{path}:{line_number}: expected a JSON object")
        records.append(value)
    if not records:
        raise DatasetError(f"{path}: no records")
    return records


def normalize_example(example: dict[str, Any]) -> dict[str, Any]:
    messages = example.get("messages")
    if not isinstance(messages, list) or not messages:
        raise DatasetError("each example must contain a non-empty messages list")

    normalized_messages: list[dict[str, Any]] = []
    for message in messages:
        if not isinstance(message, dict):
            raise DatasetError("each message must be an object")
        role = message.get("role")
        if role not in ALLOWED_ROLES:
            raise DatasetError(f"unsupported message role: {role!r}")
        normalized = dict(message)
        content = normalized.get("content")
        if isinstance(content, str):
            normalized["content"] = WHITESPACE_RE.sub(" ", content).strip()
        normalized_messages.append(normalized)

    normalized = dict(example)
    normalized["messages"] = normalized_messages
    return normalized


def _scrub_text(text: str) -> tuple[str, int]:
    replacements = 0
    scrubbed = text
    for pattern, label in (
        (EMAIL_RE, "[EMAIL]"),
        (SSN_RE, "[SSN]"),
        (PHONE_RE, "[PHONE]"),
    ):
        scrubbed, count = pattern.subn(label, scrubbed)
        replacements += count
    return scrubbed, replacements


def scrub_example(example: dict[str, Any]) -> tuple[dict[str, Any], int]:
    replacements = 0
    scrubbed = dict(example)
    messages: list[dict[str, Any]] = []
    for message in example["messages"]:
        updated = dict(message)
        content = updated.get("content")
        if isinstance(content, str):
            updated["content"], count = _scrub_text(content)
            replacements += count
        messages.append(updated)
    scrubbed["messages"] = messages
    return scrubbed, replacements


def prompt_key(example: dict[str, Any]) -> str:
    for message in example["messages"]:
        if message.get("role") == "user" and isinstance(message.get("content"), str):
            text = message["content"].lower()
            text = re.sub(r"[^a-z0-9\s]", " ", text)
            return WHITESPACE_RE.sub(" ", text).strip()
    return ""


def deduplicate(
    examples: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    seen_exact: set[str] = set()
    seen_prompts: set[str] = set()
    unique: list[dict[str, Any]] = []
    exact_duplicates = 0
    near_duplicates = 0

    for example in examples:
        exact_key = canonical_json(example)
        if exact_key in seen_exact:
            exact_duplicates += 1
            continue
        seen_exact.add(exact_key)

        key = prompt_key(example)
        if key and key in seen_prompts:
            near_duplicates += 1
            continue
        if key:
            seen_prompts.add(key)
        unique.append(example)

    return unique, exact_duplicates, near_duplicates


def eval_prompt_keys(eval_path: Path) -> set[str]:
    keys: set[str] = set()
    for record in load_jsonl(eval_path):
        prompt = record.get("prompt")
        if isinstance(prompt, str):
            text = prompt.lower()
            text = re.sub(r"[^a-z0-9\s]", " ", text)
            keys.add(WHITESPACE_RE.sub(" ", text).strip())
    return keys


def check_contamination(
    examples: list[dict[str, Any]],
    eval_keys: set[str],
    *,
    allow: bool = False,
) -> int:
    matches: list[int] = []
    for index, example in enumerate(examples):
        key = prompt_key(example)
        if key and key in eval_keys:
            matches.append(index)
    if matches and not allow:
        raise ContaminationError(
            f"{len(matches)} training prompt(s) overlap the eval set: {matches[:10]}"
        )
    return len(matches)


def split_examples(
    examples: list[dict[str, Any]],
    *,
    seed: int,
    validation_fraction: float,
    test_fraction: float,
) -> dict[str, list[dict[str, Any]]]:
    if validation_fraction < 0 or test_fraction < 0:
        raise DatasetError("split fractions must be non-negative")
    if validation_fraction + test_fraction >= 1:
        raise DatasetError("validation and test fractions must sum to less than 1")

    shuffled = list(examples)
    random.Random(seed).shuffle(shuffled)
    total = len(shuffled)
    test_count = int(total * test_fraction)
    validation_count = int(total * validation_fraction)

    if test_fraction > 0 and test_count == 0 and total >= 3:
        test_count = 1
    if validation_fraction > 0 and validation_count == 0 and total - test_count >= 3:
        validation_count = 1

    test = shuffled[:test_count]
    validation = shuffled[test_count : test_count + validation_count]
    train = shuffled[test_count + validation_count :]
    return {"train": train, "validation": validation, "test": test}


def write_jsonl(path: Path, examples: list[dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(canonical_json(example) + "\n" for example in examples).encode()
    path.write_bytes(data)
    return sha256_bytes(data)


def write_dataset_card(
    path: Path,
    manifest: DatasetManifest,
    *,
    category_counts: Counter[str],
) -> None:
    split_lines = "\n".join(
        f"| {split.name} | {split.examples} | `{split.sha256}` |" for split in manifest.splits
    )
    category_lines = "\n".join(
        f"| {category} | {count} |" for category, count in sorted(category_counts.items())
    )
    path.write_text(
        f"""# Dataset Card: {manifest.name} v{manifest.version}

## Source

- Source: {manifest.source}
- License: {manifest.license}
- Input SHA-256: `{manifest.input_sha256}`

## Processing

- Validated chat records and message roles.
- Normalized whitespace.
- Removed exact duplicates: {manifest.deduplicated}
- Removed prompt-normalized duplicates: {manifest.near_duplicates}
- PII replacements: {manifest.pii_replacements}
- Eval contamination matches: {manifest.contamination_matches}
- Seed: {manifest.seed}

## Splits

| Split | Examples | SHA-256 |
|---|---:|---|
{split_lines}

## Categories

| Category | Examples |
|---|---:|
{category_lines}

## Known limitations

- PII scrubbing is regex-based and may miss context-dependent identifiers.
- Near-duplicate detection uses normalized user prompts, not semantic similarity.
- This dataset is synthetic and does not replace human review.

## Intended use

Fine-tuning and evaluation of small tool-calling models on the issue-tracker task.

## Non-intended use

General-purpose chat, safety evaluation, or claims of frontier-model capability.
"""
    )


def prepare(
    *,
    input_path: Path,
    output_dir: Path,
    name: str,
    version: str,
    source: str,
    license_name: str,
    eval_path: Path | None,
    validation_fraction: float,
    test_fraction: float,
    seed: int,
    allow_contamination: bool = False,
) -> DatasetManifest:
    raw = load_jsonl(input_path)
    normalized = [normalize_example(example) for example in raw]

    scrubbed: list[dict[str, Any]] = []
    pii_replacements = 0
    for example in normalized:
        cleaned, replacements = scrub_example(example)
        scrubbed.append(cleaned)
        pii_replacements += replacements

    unique, exact_duplicates, near_duplicates = deduplicate(scrubbed)

    eval_keys = eval_prompt_keys(eval_path) if eval_path else set()
    contamination_matches = check_contamination(
        unique,
        eval_keys,
        allow=allow_contamination,
    )

    splits = split_examples(
        unique,
        seed=seed,
        validation_fraction=validation_fraction,
        test_fraction=test_fraction,
    )

    split_infos: list[SplitInfo] = []
    for split_name, examples in splits.items():
        split_path = output_dir / f"{split_name}.jsonl"
        digest = write_jsonl(split_path, examples)
        split_infos.append(
            SplitInfo(
                name=split_name,
                path=str(split_path),
                examples=len(examples),
                sha256=digest,
            )
        )

    manifest = DatasetManifest(
        name=name,
        version=version,
        source=source,
        license=license_name,
        input_path=str(input_path),
        input_sha256=sha256(input_path),
        seed=seed,
        created_at=datetime.now(UTC).isoformat(),
        processor_version="community-llm-ml 0.1.0",
        splits=split_infos,
        eval_path=str(eval_path) if eval_path else None,
        eval_sha256=sha256(eval_path) if eval_path else None,
        deduplicated=exact_duplicates,
        near_duplicates=near_duplicates,
        pii_replacements=pii_replacements,
        contamination_matches=contamination_matches,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "manifest.json").write_text(
        json.dumps(asdict(manifest), indent=2, sort_keys=True) + "\n"
    )

    category_counts = Counter(str(example.get("category", "uncategorized")) for example in unique)
    write_dataset_card(output_dir / "dataset-card.md", manifest, category_counts=category_counts)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", default="dataset")
    parser.add_argument("--version", default="0.1.0")
    parser.add_argument("--source", default="unspecified")
    parser.add_argument("--license", default="unspecified")
    parser.add_argument("--eval-cases", type=Path, default=None)
    parser.add_argument("--validation-fraction", type=float, default=0.05)
    parser.add_argument("--test-fraction", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--allow-contamination", action="store_true")
    args = parser.parse_args()

    manifest = prepare(
        input_path=args.input,
        output_dir=args.output_dir,
        name=args.name,
        version=args.version,
        source=args.source,
        license_name=args.license,
        eval_path=args.eval_cases,
        validation_fraction=args.validation_fraction,
        test_fraction=args.test_fraction,
        seed=args.seed,
        allow_contamination=args.allow_contamination,
    )
    print(json.dumps(asdict(manifest), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
