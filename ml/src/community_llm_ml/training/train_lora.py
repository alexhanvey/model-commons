#!/usr/bin/env python3
"""Config-driven QLoRA training entry point.

The legacy `--config` mode only validates the Phase 1 smoke config. Real runs
use a tuning recipe and require the `train` extra:

    uv run community-llm-train --recipe tuning/recipes/.../recipe.yaml \
        --output-dir runs/lora-v3
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from community_llm_ml.recipes import Recipe, load_recipe

REQUIRED = {"version", "base_model", "dataset", "training", "lora", "output"}


def load_config(path: Path) -> dict[str, Any]:
    """Load and minimally validate a legacy smoke config."""
    config = yaml.safe_load(path.read_text())
    if not isinstance(config, dict):
        raise ValueError("training config must be a mapping")
    missing = REQUIRED - config.keys()
    if missing:
        raise ValueError(f"missing config keys: {sorted(missing)}")
    return config


def _require_training_dependencies() -> None:
    missing = [
        name
        for name in (
            "torch",
            "datasets",
            "transformers",
            "peft",
            "accelerate",
        )
        if importlib.util.find_spec(name) is None
    ]
    if missing:
        raise SystemExit(
            "Missing training dependencies: "
            + ", ".join(missing)
            + ". Install with: uv sync --package community-llm-ml --extra train"
        )


def _format_example(tokenizer: Any, example: dict[str, Any]) -> str:
    messages = example.get("messages")
    if not messages:
        raise ValueError("each example must contain a non-empty messages list")
    kwargs: dict[str, Any] = {}
    if example.get("tools"):
        kwargs["tools"] = example["tools"]
    if getattr(tokenizer, "chat_template", None):
        try:
            return tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=False,
                **kwargs,
            )
        except Exception:  # noqa: BLE001
            # Tiny models and some base tokenizers do not accept tool roles.
            pass
    lines = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, str):
            lines.append(f"{message.get('role')}: {content}")
    return "\n".join(lines)


def _last_metric(history: list[dict[str, Any]], key: str) -> float | None:
    for entry in reversed(history):
        if key in entry:
            return float(entry[key])
    return None


def run_training(
    *,
    recipe: Recipe,
    recipe_path: Path,
    output_dir: Path,
    model_override: str | None,
    max_steps_override: int | None,
    max_seq_length_override: int | None,
    no_quantize: bool,
    device: str,
    target_modules: list[str] | None,
    smoke: bool,
) -> int:
    _require_training_dependencies()

    import torch
    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    if smoke and not model_override:
        model_override = "hf-internal-testing/tiny-random-LlamaForCausalLM"
    model_id = model_override or recipe.base_model.id
    revision = None if model_override else recipe.base_model.revision
    max_steps = max_steps_override or (1 if smoke else recipe.training.max_steps)
    max_seq_length = max_seq_length_override or (128 if smoke else recipe.training.max_seq_length)
    use_cuda = device != "cpu" and torch.cuda.is_available()
    quantize = use_cuda and not no_quantize and not smoke

    train_path = Path(recipe.dataset.train_uri)
    if "://" in recipe.dataset.train_uri:
        raise SystemExit("Only local dataset paths are supported by the current runner.")
    if not train_path.exists():
        raise SystemExit(f"Training dataset not found: {train_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()

    tokenizer = AutoTokenizer.from_pretrained(
        model_id,
        revision=revision,
        trust_remote_code=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    quant_config = None
    if quantize:
        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        revision=revision,
        quantization_config=quant_config,
        device_map="auto" if use_cuda else None,
        torch_dtype=torch.bfloat16 if use_cuda else torch.float32,
        trust_remote_code=False,
    )
    if quantize:
        model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False

    lora_config = LoraConfig(
        r=recipe.lora.r,
        lora_alpha=recipe.lora.alpha,
        lora_dropout=recipe.lora.dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=target_modules or ["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files=str(train_path), split="train")
    validation_fraction = recipe.training.validation_fraction
    if validation_fraction > 0 and len(dataset) > 1:
        split = dataset.train_test_split(
            test_size=validation_fraction,
            seed=recipe.training.seed,
        )
        train_raw, eval_raw = split["train"], split["test"]
    else:
        train_raw, eval_raw = dataset, None

    def tokenize(example: dict[str, Any]) -> dict[str, Any]:
        text = _format_example(tokenizer, example)
        return tokenizer(
            text,
            truncation=True,
            max_length=max_seq_length,
            padding=False,
        )

    train_dataset = train_raw.map(tokenize, remove_columns=train_raw.column_names)
    eval_dataset = (
        eval_raw.map(tokenize, remove_columns=eval_raw.column_names)
        if eval_raw is not None
        else None
    )
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        max_steps=max_steps,
        per_device_train_batch_size=recipe.training.batch_size,
        gradient_accumulation_steps=recipe.training.gradient_accumulation_steps,
        learning_rate=recipe.training.learning_rate,
        logging_steps=1,
        save_strategy="steps",
        save_steps=recipe.output.save_steps,
        save_total_limit=1,
        eval_strategy="steps" if eval_dataset is not None else "no",
        eval_steps=recipe.output.save_steps if eval_dataset is not None else None,
        report_to=[],
        seed=recipe.training.seed,
        bf16=use_cuda,
        use_cpu=not use_cuda,
        gradient_checkpointing=use_cuda,
        remove_unused_columns=False,
    )
    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
    )
    trainer.train()

    adapter_dir = output_dir / "adapter"
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)

    runtime = time.monotonic() - started
    history = trainer.state.log_history
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"
    metrics = {
        "recipe": recipe.name,
        "base_model": model_id,
        "base_revision": revision,
        "dataset_sha256": recipe.dataset.train_sha256,
        "eval_sha256": recipe.eval.cases_sha256,
        "train_examples": len(train_dataset),
        "eval_examples": len(eval_dataset) if eval_dataset is not None else 0,
        "max_steps": max_steps,
        "max_seq_length": max_seq_length,
        "train_loss": _last_metric(history, "loss"),
        "eval_loss": _last_metric(history, "eval_loss"),
        "runtime_seconds": runtime,
        "gpu": gpu_name,
        "quantized": quantize,
        "smoke": smoke,
        "completed_at": datetime.now(UTC).isoformat(),
        "python": platform.python_version(),
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
        "recipe_path": str(recipe_path),
    }
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recipe", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("runs/lora"))
    parser.add_argument("--model-override", default=None)
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--max-seq-length", type=int, default=None)
    parser.add_argument("--no-quantize", action="store_true")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    parser.add_argument("--target-modules", default=None)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    if args.recipe is None:
        if args.config is None:
            parser.error("pass --recipe or --config")
        config = load_config(args.config)
        args.output_dir.mkdir(parents=True, exist_ok=True)
        summary = {
            "config": str(args.config),
            "run_name": config.get("run_name"),
            "method": config["training"].get("method"),
            "max_steps": config["training"].get("max_steps"),
            "max_seq_length": config["training"].get("max_seq_length"),
            "output_dir": str(args.output_dir),
        }
        (args.output_dir / "config_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary, indent=2))
        return 0

    recipe = load_recipe(args.recipe)
    target_modules = (
        [item.strip() for item in args.target_modules.split(",") if item.strip()]
        if args.target_modules
        else None
    )
    if args.smoke and target_modules is None:
        target_modules = ["q_proj", "v_proj"]

    return run_training(
        recipe=recipe,
        recipe_path=args.recipe,
        output_dir=args.output_dir,
        model_override=args.model_override,
        max_steps_override=args.max_steps,
        max_seq_length_override=args.max_seq_length,
        no_quantize=args.no_quantize,
        device=args.device,
        target_modules=target_modules,
        smoke=args.smoke,
    )


if __name__ == "__main__":
    raise SystemExit(main())
