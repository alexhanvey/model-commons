#!/usr/bin/env python3
"""Evaluate tool-calling behavior against a held-out JSONL set.

Supports:
- single tool calls
- multiple tool calls
- no-tool cases
- clarification cases
- final answers after a tool result
- JSON schema validation
- forbidden tools
- per-category scoring
"""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from openai import OpenAI

CLARIFY_RE = re.compile(
    r"\?|clarify|which|what|where|when|who|provide|specify|need|please",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="Qwen/Qwen3-1.7B")
    parser.add_argument("--data", default="data/hard_heldout_tools.jsonl")
    parser.add_argument("--output", default="runs/tool-call-eval.json")
    parser.add_argument("--api-key", default="local")
    parser.add_argument("--max-tokens", type=int, default=1024)
    return parser.parse_args()


def normalize_call(call: Any) -> dict[str, Any]:
    if not isinstance(call, dict):
        return {"name": None, "arguments": None, "raw": call}
    if "function" in call and isinstance(call["function"], dict):
        name = call["function"].get("name")
        args = call["function"].get("arguments")
    else:
        name = call.get("name") or call.get("tool")
        args = call.get("arguments") or call.get("parameters")
    if isinstance(args, str):
        try:
            args = json.loads(args)
        except json.JSONDecodeError:
            args = None
    return {"name": name, "arguments": args, "raw": call}


def extract_calls(message: Any) -> tuple[list[dict[str, Any]], str, str]:
    tool_calls = getattr(message, "tool_calls", None)
    if tool_calls:
        return [normalize_call(call.model_dump()) for call in tool_calls], "tool_calls"

    content = getattr(message, "content", None) or ""
    if isinstance(content, list):
        content = " ".join(str(item) for item in content)
    content = str(content)

    candidates = [content]
    match = re.search(r"(\{.*\}|\[.*\])", content, re.DOTALL)
    if match:
        candidates.insert(0, match.group(0))

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, list):
            return [normalize_call(item) for item in payload], "content_json"
        if isinstance(payload, dict):
            if "tool_calls" in payload and isinstance(payload["tool_calls"], list):
                return [normalize_call(item) for item in payload["tool_calls"]], "content_json"
            if "tool" in payload or "name" in payload:
                return [normalize_call(payload)], "content_json"

    return [], "no_tool_call"


def tool_schema(tools: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for item in tools:
        function = item.get("function", {})
        if function.get("name") == name:
            return function.get("parameters", {})
    return None


def schema_valid(tools: list[dict[str, Any]], call: dict[str, Any]) -> bool:
    name = call.get("name")
    arguments = call.get("arguments")
    if not name or arguments is None:
        return False
    schema = tool_schema(tools, name)
    if not schema:
        return False
    try:
        Draft202012Validator(schema).validate(arguments)
    except Exception:  # noqa: BLE001
        return False
    return True


def values_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return float(actual) == float(expected)
    if isinstance(expected, str) and isinstance(actual, str):
        return actual.strip().lower() == expected.strip().lower()
    return actual == expected


def arguments_match(
    expected: dict[str, Any],
    actual: dict[str, Any] | None,
    strict: bool,
) -> bool:
    if actual is None:
        return False
    for key, expected_value in expected.items():
        if key not in actual or not values_equal(actual[key], expected_value):
            return False
    return not (strict and set(actual) != set(expected))


def expected_calls(row: dict[str, Any]) -> list[dict[str, Any]]:
    expected = row.get("expected", {})
    if "calls" in expected:
        return expected["calls"]
    if "name" in expected:
        return [{"name": expected["name"], "arguments": expected.get("arguments", {})}]
    return []


def expected_type(row: dict[str, Any]) -> str:
    expected = row.get("expected", {})
    if "type" in expected:
        return expected["type"]
    if "calls" in expected or "name" in expected:
        return "tool_call"
    return "tool_call"


def score_case(
    row: dict[str, Any],
    calls: list[dict[str, Any]],
    content: str,
) -> tuple[bool, str]:
    kind = expected_type(row)
    expected = row.get("expected", {})
    forbidden = set(row.get("forbidden_tools", []))

    if forbidden:
        actual_names = {call.get("name") for call in calls}
        if actual_names & forbidden:
            return False, f"forbidden tool called: {sorted(actual_names & forbidden)}"

    if kind == "no_tool":
        if calls:
            return False, "expected no tool call"
        if not content.strip():
            return False, "expected a text answer, got empty content"
        return True, "no tool call"

    if kind == "clarify":
        if calls:
            return False, "expected clarification, got a tool call"
        if not CLARIFY_RE.search(content):
            return False, "expected a clarification question"
        return True, "clarification"

    if kind == "final_answer":
        if calls:
            return False, "expected final answer, got another tool call"
        contains = expected.get("contains", [])
        missing = [text for text in contains if text.lower() not in content.lower()]
        if missing:
            return False, f"final answer missing: {missing}"
        return True, "final answer"

    wanted = expected_calls(row)
    if len(calls) != len(wanted):
        return False, f"expected {len(wanted)} calls, got {len(calls)}"

    strict = bool(row.get("strict_arguments", False))
    used: set[int] = set()
    for wanted_call in wanted:
        match_index = None
        for index, actual_call in enumerate(calls):
            if index in used:
                continue
            if actual_call.get("name") != wanted_call.get("name"):
                continue
            if arguments_match(
                wanted_call.get("arguments", {}),
                actual_call.get("arguments"),
                strict,
            ):
                match_index = index
                break
        if match_index is None:
            return False, f"missing or mismatched call for {wanted_call.get('name')}"
        used.add(match_index)

    for call in calls:
        if not schema_valid(row.get("tools", []), call):
            return False, f"arguments do not match schema for {call.get('name')}"

    return True, "tool call"


def main() -> int:
    args = parse_args()
    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    rows = [json.loads(line) for line in Path(args.data).read_text().splitlines() if line.strip()]

    results = []
    category_totals: Counter[str] = Counter()
    category_passes: Counter[str] = Counter()

    for row in rows:
        category = row.get("category", "uncategorized")
        if "messages" in row:
            messages = row["messages"]
        else:
            messages = [
                {
                    "role": "system",
                    "content": "You are a precise tool-calling assistant.",
                },
                {"role": "user", "content": row["prompt"]},
            ]

        request: dict[str, Any] = {
            "model": args.model,
            "messages": messages,
            "temperature": 0.0,
            "max_tokens": args.max_tokens,
        }
        if row.get("tools"):
            request["tools"] = row["tools"]
            request["tool_choice"] = "auto"

        started = time.perf_counter()
        response = client.chat.completions.create(**request)
        latency_ms = (time.perf_counter() - started) * 1000
        message = response.choices[0].message
        calls, source = extract_calls(message)
        content = getattr(message, "content", None) or ""
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        content = str(content)

        passed, reason = score_case(row, calls, content)
        category_totals[category] += 1
        if passed:
            category_passes[category] += 1

        results.append(
            {
                "id": row.get("id"),
                "category": category,
                "passed": passed,
                "reason": reason,
                "expected": row.get("expected"),
                "actual": {"calls": calls, "content": content, "source": source},
                "latency_ms": round(latency_ms, 1),
            }
        )

    passed = sum(1 for item in results if item["passed"])
    summary = {
        "model": args.model,
        "data": args.data,
        "total": len(results),
        "passed": passed,
        "valid_tool_call_rate": passed / len(results) if results else 0.0,
        "p50_latency_ms": sorted(item["latency_ms"] for item in results)[len(results) // 2]
        if results
        else 0.0,
        "categories": {
            category: {
                "total": category_totals[category],
                "passed": category_passes[category],
                "rate": category_passes[category] / category_totals[category]
                if category_totals[category]
                else 0.0,
            }
            for category in sorted(category_totals)
        },
        "results": results,
    }

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(summary, indent=2, default=str))
    printable = {
        key: summary[key]
        for key in (
            "model",
            "total",
            "passed",
            "valid_tool_call_rate",
            "p50_latency_ms",
            "categories",
        )
    }
    print(json.dumps(printable, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
