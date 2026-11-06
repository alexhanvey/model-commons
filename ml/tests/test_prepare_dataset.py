from __future__ import annotations

import json
from pathlib import Path

import pytest
from community_llm_ml.data.prepare_dataset import (
    ContaminationError,
    check_contamination,
    deduplicate,
    eval_prompt_keys,
    load_jsonl,
    normalize_example,
    prepare,
    scrub_example,
    split_examples,
)


def example(prompt: str, answer: str = "ok", category: str = "single_tool") -> dict:
    return {
        "category": category,
        "messages": [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ],
    }


def test_normalize_and_scrub() -> None:
    normalized = normalize_example(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "  email a@example.com or call +1 555 123 4567  ",
                },
                {"role": "assistant", "content": "ok"},
            ]
        }
    )
    scrubbed, replacements = scrub_example(normalized)

    content = scrubbed["messages"][0]["content"]
    assert "a@example.com" not in content
    assert "[EMAIL]" in content
    assert "[PHONE]" in content
    assert replacements >= 2


def test_deduplicate_exact_and_near_duplicates() -> None:
    examples = [
        example("List the projects I can access."),
        example("List the projects I can access."),
        example("list the projects i can access!"),
        example("Who am I signed in as?"),
    ]

    unique, exact, near = deduplicate(examples)

    assert len(unique) == 2
    assert exact == 1
    assert near == 1


def test_contamination_detection(tmp_path: Path) -> None:
    eval_path = tmp_path / "eval.jsonl"
    eval_path.write_text(
        json.dumps({"id": "e1", "prompt": "List the projects I can access."}) + "\n"
    )
    keys = eval_prompt_keys(eval_path)
    examples = [example("list the projects i can access")]

    with pytest.raises(ContaminationError):
        check_contamination(examples, keys)

    assert check_contamination(examples, keys, allow=True) == 1


def test_split_is_deterministic() -> None:
    examples = [example(f"prompt {index}") for index in range(20)]
    first = split_examples(
        examples,
        seed=7,
        validation_fraction=0.1,
        test_fraction=0.1,
    )
    second = split_examples(
        examples,
        seed=7,
        validation_fraction=0.1,
        test_fraction=0.1,
    )

    assert first == second
    assert len(first["train"]) == 16
    assert len(first["validation"]) == 2
    assert len(first["test"]) == 2


def test_prepare_writes_manifest_and_card(tmp_path: Path) -> None:
    input_path = tmp_path / "train.jsonl"
    input_path.write_text(
        "\n".join(json.dumps(example(f"prompt {index}")) for index in range(10)) + "\n"
    )
    eval_path = tmp_path / "eval.jsonl"
    eval_path.write_text(json.dumps({"id": "e1", "prompt": "different prompt"}) + "\n")
    output_dir = tmp_path / "prepared"

    manifest = prepare(
        input_path=input_path,
        output_dir=output_dir,
        name="smoke",
        version="0.1.0",
        source="unit test",
        license_name="Apache-2.0",
        eval_path=eval_path,
        validation_fraction=0.1,
        test_fraction=0.1,
        seed=3,
    )

    assert manifest.contamination_matches == 0
    assert (output_dir / "train.jsonl").exists()
    assert (output_dir / "validation.jsonl").exists()
    assert (output_dir / "test.jsonl").exists()
    assert (output_dir / "manifest.json").exists()
    assert (output_dir / "dataset-card.md").exists()
    assert len(load_jsonl(output_dir / "train.jsonl")) == 8
    assert "Dataset Card: smoke v0.1.0" in (output_dir / "dataset-card.md").read_text()
