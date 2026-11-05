#!/usr/bin/env python3
"""Build a balanced training mix: ToolACE tool calls plus synthetic restraint.

The synthetic examples teach the model:
- when not to call a tool
- when to ask for missing arguments
- how to issue multiple tool calls

They are intentionally separate from the hard held-out evaluation set.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any


def tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


WEATHER = tool(
    "get_weather",
    "Get current weather for a city.",
    {
        "city": {"type": "string"},
        "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]},
    },
    ["city"],
)
SEARCH = tool(
    "search_docs",
    "Search project documentation.",
    {"query": {"type": "string"}, "limit": {"type": "integer"}},
    ["query"],
)
STOCK = tool(
    "get_stock_price",
    "Get the current stock price for a ticker symbol.",
    {"symbol": {"type": "string"}},
    ["symbol"],
)
CONVERT = tool(
    "convert_units",
    "Convert a value between units.",
    {
        "value": {"type": "number"},
        "from_unit": {"type": "string"},
        "to_unit": {"type": "string"},
    },
    ["value", "from_unit", "to_unit"],
)
REMINDER = tool(
    "create_reminder",
    "Create a reminder.",
    {"title": {"type": "string"}, "when": {"type": "string"}},
    ["title", "when"],
)
FLIGHT = tool(
    "book_flight",
    "Book a flight.",
    {
        "origin": {"type": "string"},
        "destination": {"type": "string"},
        "date": {"type": "string"},
        "passengers": {"type": "integer"},
    },
    ["origin", "destination", "date", "passengers"],
)
EMAIL = tool(
    "send_email",
    "Send an email.",
    {
        "to": {"type": "string"},
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    ["to", "subject", "body"],
)
THERMOSTAT = tool(
    "set_thermostat",
    "Set the thermostat temperature and mode.",
    {
        "temperature": {"type": "number"},
        "mode": {"type": "string", "enum": ["heat", "cool", "auto"]},
    },
    ["temperature", "mode"],
)

BASE_TOOLS = [WEATHER, SEARCH, STOCK]
MULTI_TOOLS = [WEATHER, SEARCH, STOCK, CONVERT, REMINDER, THERMOSTAT]
CLARIFY_TOOLS = [FLIGHT, EMAIL, REMINDER, WEATHER]

NO_TOOL_PROMPTS = [
    "Give me a fun fact about octopuses.",
    "Explain Docker in one paragraph.",
    "Write a limerick about coffee.",
    "What's the capital of France?",
    "Summarize why tests matter.",
    "Tell me a short story about a robot.",
    "What does HTTP stand for?",
    "Give me three naming ideas for a small model.",
    "Explain the difference between latency and throughput.",
    "Write a two-sentence welcome message for a developer tool.",
]

CLARIFY_PROMPTS = [
    "Book a flight for me.",
    "Send an email to my boss.",
    "Set a reminder.",
    "What's the weather like?",
    "Translate something for me.",
    "Create a calendar event.",
    "Cancel my order.",
    "Play some music.",
]

MULTI_CASES: list[tuple[str, list[dict[str, Any]], list[dict[str, Any]]]] = [
    (
        "Check the weather in Rome and find docs about trains.",
        MULTI_TOOLS,
        [
            {"name": "get_weather", "arguments": {"city": "Rome"}},
            {"name": "search_docs", "arguments": {"query": "trains"}},
        ],
    ),
    (
        "Get MSFT and NVDA stock prices.",
        MULTI_TOOLS,
        [
            {"name": "get_stock_price", "arguments": {"symbol": "MSFT"}},
            {"name": "get_stock_price", "arguments": {"symbol": "NVDA"}},
        ],
    ),
    (
        "Convert 3 miles to kilometers and 2 kilograms to pounds.",
        MULTI_TOOLS,
        [
            {
                "name": "convert_units",
                "arguments": {"value": 3, "from_unit": "miles", "to_unit": "kilometers"},
            },
            {
                "name": "convert_units",
                "arguments": {"value": 2, "from_unit": "kilograms", "to_unit": "pounds"},
            },
        ],
    ),
    (
        "What's the weather in Oslo and remind me to pack at 6pm?",
        MULTI_TOOLS,
        [
            {"name": "get_weather", "arguments": {"city": "Oslo"}},
            {"name": "create_reminder", "arguments": {"title": "pack", "when": "6pm"}},
        ],
    ),
    (
        "Search docs for backups and set the thermostat to 19 in auto mode.",
        MULTI_TOOLS,
        [
            {"name": "search_docs", "arguments": {"query": "backups"}},
            {"name": "set_thermostat", "arguments": {"temperature": 19, "mode": "auto"}},
        ],
    ),
]


def assistant_text(text: str) -> dict[str, Any]:
    return {"role": "assistant", "content": text}


def assistant_calls(calls: list[dict[str, Any]], index: int) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": f"call_synth_{index}_{call_index}",
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": json.dumps(call["arguments"], ensure_ascii=False),
                },
            }
            for call_index, call in enumerate(calls)
        ],
    }


def example(
    messages: list[dict[str, Any]], tools: list[dict[str, Any]], source: str
) -> dict[str, Any]:
    return {
        "messages": [{"role": "system", "content": "You are a precise tool-calling assistant."}]
        + messages,
        "tools": tools,
        "metadata": {"source": source},
    }


def build_synthetic() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = []
    for prompt in NO_TOOL_PROMPTS * 20:
        examples.append(
            example(
                [
                    {"role": "user", "content": prompt},
                    assistant_text("I can answer that directly without using a tool."),
                ],
                BASE_TOOLS,
                "synthetic_no_tool",
            )
        )
    for prompt in CLARIFY_PROMPTS * 20:
        examples.append(
            example(
                [
                    {"role": "user", "content": prompt},
                    assistant_text(
                        "I need a bit more information: which specific details should I use?"
                    ),
                ],
                CLARIFY_TOOLS,
                "synthetic_clarify",
            )
        )
    for index, (prompt, tools, calls) in enumerate(MULTI_CASES * 20):
        examples.append(
            example(
                [
                    {"role": "user", "content": prompt},
                    assistant_calls(calls, index),
                ],
                tools,
                "synthetic_multi_tool",
            )
        )
    return examples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--toolace", default="data/toolace_sft_1000.jsonl")
    parser.add_argument("--output", default="data/train_mix_v1.jsonl")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-tool-ratio", type=float, default=0.15)
    parser.add_argument("--clarify-ratio", type=float, default=0.10)
    parser.add_argument("--multi-tool-ratio", type=float, default=0.10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    toolace = [
        json.loads(line) for line in Path(args.toolace).read_text().splitlines() if line.strip()
    ]
    synthetic = build_synthetic()

    by_source: dict[str, list[dict[str, Any]]] = {}
    for item in synthetic:
        by_source.setdefault(item["metadata"]["source"], []).append(item)

    target_total = len(toolace)

    def take(source: str, ratio: float) -> list[dict[str, Any]]:
        population = by_source[source]
        count = min(len(population), int(target_total * ratio))
        return rng.sample(population, count)

    no_tool = take("synthetic_no_tool", args.no_tool_ratio)
    clarify = take("synthetic_clarify", args.clarify_ratio)
    multi = take("synthetic_multi_tool", args.multi_tool_ratio)

    mixed = toolace + no_tool + clarify + multi
    rng.shuffle(mixed)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for item in mixed:
            handle.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n")

    print(
        json.dumps(
            {
                "toolace": len(toolace),
                "no_tool": len(no_tool),
                "clarify": len(clarify),
                "multi_tool": len(multi),
                "total": len(mixed),
                "output": str(output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
