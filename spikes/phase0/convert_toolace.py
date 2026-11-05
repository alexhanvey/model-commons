#!/usr/bin/env python3
"""Convert ToolACE examples into the project's chat/tool-call schema.

ToolACE is Apache-2.0:
https://huggingface.co/datasets/Team-ACE/ToolACE

The conversion is intentionally conservative: examples that cannot be parsed
cleanly are skipped and counted.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

SYSTEM_PROMPT = (
    "You are a precise tool-calling assistant. Call the right tool with valid JSON arguments."
)


def normalize_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [normalize_schema(item) for item in value]
    if not isinstance(value, dict):
        return value
    result = {key: normalize_schema(item) for key, item in value.items()}
    if result.get("type") == "dict":
        result["type"] = "object"
    if result.get("required") is None:
        result.pop("required", None)
    return result


def extract_tools(system: str) -> list[dict[str, Any]]:
    marker = "functions in JSON format"
    marker_index = system.find(marker)
    if marker_index == -1:
        return []
    start = system.find("[", marker_index)
    if start == -1:
        return []
    try:
        raw_tools, _ = json.JSONDecoder().raw_decode(system[start:])
    except json.JSONDecodeError:
        return []

    tools = []
    for raw in raw_tools:
        if not isinstance(raw, dict) or "name" not in raw:
            continue
        parameters = normalize_schema(raw.get("parameters") or {"type": "object", "properties": {}})
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": raw["name"],
                    "description": raw.get("description", ""),
                    "parameters": parameters,
                },
            }
        )
    return tools


def split_top_level(text: str, delimiter: str = ",") -> list[str]:
    parts: list[str] = []
    buffer: list[str] = []
    depth = 0
    quote: str | None = None
    escaped = False

    for char in text:
        if quote:
            buffer.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char in {"'", '"'}:
            quote = char
            buffer.append(char)
        elif char in "([{":
            depth += 1
            buffer.append(char)
        elif char in ")]}":
            depth -= 1
            buffer.append(char)
        elif char == delimiter and depth == 0:
            parts.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)

    if buffer:
        parts.append("".join(buffer).strip())
    return [part for part in parts if part]


def find_matching(text: str, start: int, open_char: str, close_char: str) -> int:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == open_char:
            depth += 1
        elif char == close_char:
            depth -= 1
            if depth == 0:
                return index
    return -1


def parse_value(text: str) -> Any:
    text = text.strip()
    if text in {"true", "True"}:
        return True
    if text in {"false", "False"}:
        return False
    if text in {"null", "None"}:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text.strip("'\"")


def parse_kwargs(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for part in split_top_level(text):
        depth = 0
        quote: str | None = None
        escaped = False
        split_at = -1
        for index, char in enumerate(part):
            if quote:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == quote:
                    quote = None
                continue
            if char in {"'", '"'}:
                quote = char
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                depth -= 1
            elif char == "=" and depth == 0:
                split_at = index
                break
        if split_at == -1:
            result["value"] = parse_value(part)
            continue
        key = part[:split_at].strip()
        value = part[split_at + 1 :].strip()
        result[key] = parse_value(value)
    return result


def parse_calls(value: str) -> list[dict[str, Any]]:
    text = value.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return []
    inner = text[1:-1].strip()
    calls: list[dict[str, Any]] = []
    index = 0
    while index < len(inner):
        while index < len(inner) and inner[index] in " ,\n\t":
            index += 1
        open_paren = inner.find("(", index)
        if open_paren == -1:
            break
        name = inner[index:open_paren].strip().strip(",")
        close_paren = find_matching(inner, open_paren, "(", ")")
        if close_paren == -1:
            break
        args = parse_kwargs(inner[open_paren + 1 : close_paren])
        if name:
            calls.append({"name": name, "arguments": args})
        index = close_paren + 1
    return calls


def convert_row(row: dict[str, Any], index: int) -> dict[str, Any] | None:
    system = row.get("system") or ""
    tools = extract_tools(system)
    if not tools:
        return None

    conversations = row.get("conversations") or []
    user_message: str | None = None
    assistant_calls: list[dict[str, Any]] | None = None

    for message in conversations:
        role = message.get("from")
        value = message.get("value") or ""
        if role == "user" and user_message is None:
            user_message = value
        elif role == "assistant" and user_message is not None and value.strip().startswith("["):
            calls = parse_calls(value)
            if calls:
                assistant_calls = calls
                break

    if not user_message or not assistant_calls:
        return None

    tool_names = {item["function"]["name"] for item in tools}
    if any(call["name"] not in tool_names for call in assistant_calls):
        return None

    tool_calls = [
        {
            "id": f"call_{index}_{call_index}",
            "type": "function",
            "function": {
                "name": call["name"],
                "arguments": json.dumps(call["arguments"], ensure_ascii=False),
            },
        }
        for call_index, call in enumerate(assistant_calls)
    ]

    return {
        "id": f"toolace-{index}",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": "", "tool_calls": tool_calls},
        ],
        "tools": tools,
        "metadata": {"source": "Team-ACE/ToolACE", "license": "Apache-2.0"},
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/toolace_sft.jsonl")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--max-tools", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    from datasets import load_dataset

    args = parse_args()
    dataset = load_dataset("Team-ACE/ToolACE", split="train")
    total = min(args.limit, len(dataset))

    converted = 0
    skipped = 0
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with Path(args.output).open("w") as handle:
        for index in range(total):
            row = dataset[index]
            example = convert_row(row, index)
            if not example:
                skipped += 1
                continue
            if len(example["tools"]) > args.max_tools:
                skipped += 1
                continue
            handle.write(json.dumps(example, ensure_ascii=False, separators=(",", ":")) + "\n")
            converted += 1

    print(
        json.dumps(
            {"total": total, "converted": converted, "skipped": skipped, "output": args.output},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
