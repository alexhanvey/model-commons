#!/usr/bin/env python3
"""A small, single-GPU QLoRA smoke test for Phase 0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--data", default="data/tool_call_smoke.jsonl")
    parser.add_argument("--output-dir", default="runs/lora-smoke")
    parser.add_argument("--max-steps", type=int, default=10)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=32)
    parser.add_argument("--lora-dropout", type=float, default=0.05)
    parser.add_argument("--validation-fraction", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def format_example(tokenizer, example: dict) -> str:
    messages = example.get("messages")
    if not messages:
        raise ValueError("Each example must contain a non-empty `messages` list")
    kwargs = {}
    if example.get("tools"):
        kwargs["tools"] = example["tools"]
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
        **kwargs,
    )


def main() -> int:
    args = parse_args()

    if not torch.cuda.is_available():
        raise SystemExit("CUDA is required for the QLoRA smoke test.")

    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"

    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=quant_config,
        device_map="auto",
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model)
    model.config.use_cache = False

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = load_dataset("json", data_files=args.data, split="train")
    if args.validation_fraction > 0 and len(dataset) > 1:
        split = dataset.train_test_split(test_size=args.validation_fraction, seed=args.seed)
        train_raw, eval_raw = split["train"], split["test"]
    else:
        train_raw, eval_raw = dataset, None

    def tokenize(example: dict) -> dict:
        text = format_example(tokenizer, example)
        return tokenizer(
            text,
            truncation=True,
            max_length=args.max_seq_length,
            padding=False,
        )

    train_dataset = train_raw.map(tokenize, remove_columns=train_raw.column_names)
    eval_dataset = None
    if eval_raw is not None:
        eval_dataset = eval_raw.map(tokenize, remove_columns=eval_raw.column_names)
    collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    training_args = TrainingArguments(
        output_dir=args.output_dir,
        max_steps=args.max_steps,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=args.learning_rate,
        logging_steps=1,
        save_strategy="steps",
        save_steps=max(1, args.max_steps),
        save_total_limit=1,
        report_to=[],
        remove_unused_columns=False,
        bf16=torch.cuda.is_bf16_supported(),
        fp16=not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        eval_strategy="steps" if eval_dataset is not None else "no",
        eval_steps=max(1, args.max_steps // 5),
        per_device_eval_batch_size=1,
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=collator,
    )
    result = trainer.train()
    eval_metrics = trainer.evaluate() if eval_dataset is not None else {}

    model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    metrics = {
        "model": args.model,
        "data": args.data,
        "max_steps": args.max_steps,
        "max_seq_length": args.max_seq_length,
        "train_metrics": result.metrics,
        "eval_metrics": eval_metrics,
        "gpu": torch.cuda.get_device_name(0),
        "vram_gib": torch.cuda.get_device_properties(0).total_memory / 1024**3,
    }
    (Path(args.output_dir) / "metrics.json").write_text(json.dumps(metrics, indent=2, default=str))
    print(json.dumps(metrics, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
