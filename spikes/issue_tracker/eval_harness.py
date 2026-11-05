#!/usr/bin/env python3
"""State-based evaluation harness for the issue-tracker tool-use task."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from mock_api import MockTracker, ToolError
from openai import OpenAI
from schemas import TOOLS, tool_schema

CLARIFY_RE = re.compile(
    r"\?|which|what|where|when|who|provide|specify|need|please|confirm|reopen",
    re.IGNORECASE,
)
SYSTEM_PROMPT = (
    "You are a cautious issue-tracker assistant. Use only the provided tools. "
    "Never invent issue IDs, project IDs, or user IDs. Ask for missing information. "
    "Ask for explicit confirmation before closing or reopening an issue. "
    "Do not call get_current_user or list_projects unless the user explicitly asks for identity or the project list. "
    "Use the minimum number of tools needed."
)

EXPLORATION_TOOLS = {"get_current_user", "list_projects", "list_users"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", default="ibm-granite/granite-4.1-3b")
    parser.add_argument("--api-key", default="local")
    parser.add_argument("--data", default="eval_cases.jsonl")
    parser.add_argument("--output", default="results/granite-base-eval.json")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=1024)
    parser.add_argument("--temperature", type=float, default=0.0)
    return parser.parse_args()


def normalize_call(call: Any) -> dict[str, Any]:
    if not isinstance(call, dict):
        return {"name": None, "arguments": None, "id": None, "raw": call}
    function = call.get("function") or {}
    name = function.get("name") or call.get("name")
    arguments = function.get("arguments") if "function" in call else call.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = None
    return {"name": name, "arguments": arguments, "id": call.get("id"), "raw": call}


def values_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        return float(actual) == float(expected)
    if isinstance(expected, str) and isinstance(actual, str):
        return actual.strip().lower() == expected.strip().lower()
    return actual == expected


def arguments_match(expected: dict[str, Any], actual: dict[str, Any] | None, strict: bool) -> bool:
    if actual is None:
        return False
    for key, expected_value in expected.items():
        if key not in actual or not values_equal(actual[key], expected_value):
            return False
    return not (strict and set(actual) != set(expected))


def schema_valid(call: dict[str, Any]) -> bool:
    name = call.get("name")
    arguments = call.get("arguments")
    schema = tool_schema(name or "")
    if not schema or arguments is None:
        return False
    try:
        Draft202012Validator(schema).validate(arguments)
    except Exception:  # noqa: BLE001
        return False
    return True


def check_state(tracker: MockTracker, expected_state: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    state = tracker.snapshot()
    issues = {issue["id"]: issue for issue in state["issues"]}

    for issue_id, fields in (expected_state.get("issues") or {}).items():
        issue = issues.get(issue_id)
        if issue is None:
            errors.append(f"missing issue {issue_id}")
            continue
        for field, value in fields.items():
            if field == "labels_contains":
                missing = [label for label in value if label not in issue["labels"]]
                if missing:
                    errors.append(f"{issue_id} missing labels {missing}")
            elif field == "comments_contain":
                texts = " ".join(comment["body"] for comment in issue["comments"]).lower()
                missing = [text for text in value if text.lower() not in texts]
                if missing:
                    errors.append(f"{issue_id} missing comments {missing}")
            else:
                actual = issue.get(field)
                if not values_equal(actual, value):
                    errors.append(f"{issue_id}.{field}: expected {value!r}, got {actual!r}")

    created = expected_state.get("created_issue")
    if created:
        title = created.get("title")
        match = [
            issue
            for issue in state["issues"]
            if title and issue["title"].strip().lower() == title.strip().lower()
        ]
        if not match:
            errors.append(f"created issue not found: {title}")
        else:
            issue = match[0]
            for field, value in created.items():
                if field == "title":
                    continue
                actual = issue.get(field)
                if not values_equal(actual, value):
                    errors.append(f"created_issue.{field}: expected {value!r}, got {actual!r}")

    return errors


def score_case(
    case: dict[str, Any],
    executed: list[dict[str, Any]],
    content: str,
    tracker: MockTracker,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    expected = case.get("expected", {})
    kind = expected.get("type", "tool_call")

    expected_calls = expected.get("calls", [])
    expected_names = {call.get("name") for call in expected_calls}
    effective_executed = [
        call
        for call in executed
        if not (call.get("name") in EXPLORATION_TOOLS and call.get("name") not in expected_names)
    ]

    forbidden = set(case.get("forbidden_tools", []))
    if forbidden:
        called = {call.get("name") for call in executed}
        if called & forbidden:
            errors.append(f"forbidden tools called: {sorted(called & forbidden)}")

    if kind == "no_tool":
        if effective_executed:
            errors.append(
                f"expected no tool calls, got {[call.get('name') for call in effective_executed]}"
            )
        if not content.strip():
            errors.append("expected a text answer, got empty content")
    elif kind == "clarify":
        if effective_executed:
            errors.append(
                f"expected clarification, got tool calls {[call.get('name') for call in effective_executed]}"
            )
        if not CLARIFY_RE.search(content):
            errors.append("expected a clarification or confirmation question")
    elif kind == "final_answer":
        if effective_executed:
            errors.append("expected a final answer, got another tool call")
        for text in expected.get("contains", []):
            if text.lower() not in content.lower():
                errors.append(f"final answer missing {text!r}")
    else:
        wanted = expected_calls
        if len(effective_executed) != len(wanted):
            errors.append(f"expected {len(wanted)} calls, got {len(effective_executed)}")
        for index, expected_call in enumerate(wanted):
            if index >= len(effective_executed):
                break
            actual_call = effective_executed[index]
            if actual_call.get("name") != expected_call.get("name"):
                errors.append(
                    f"call {index}: expected {expected_call.get('name')}, got {actual_call.get('name')}"
                )
                continue
            if not arguments_match(
                expected_call.get("arguments", {}),
                actual_call.get("arguments"),
                bool(case.get("strict_arguments", False)),
            ):
                errors.append(f"call {index}: arguments mismatch for {expected_call.get('name')}")

    for call in executed:
        if not schema_valid(call):
            errors.append(f"invalid schema for {call.get('name')}")

    errors.extend(check_state(tracker, expected.get("final_state", {})))
    return not errors, errors


def run_case(client: OpenAI, args: argparse.Namespace, case: dict[str, Any]) -> dict[str, Any]:
    tracker = MockTracker()
    tracker.reset()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": case["prompt"]},
    ]
    executed: list[dict[str, Any]] = []
    tool_errors: list[str] = []
    content = ""
    started = time.perf_counter()

    for _ in range(args.max_steps):
        response = client.chat.completions.create(
            model=args.model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        message = response.choices[0].message
        content = message.content or ""
        if isinstance(content, list):
            content = " ".join(str(item) for item in content)
        content = str(content)

        if not message.tool_calls:
            break

        messages.append(message.model_dump(exclude_none=True))
        for raw_call in message.tool_calls:
            call = normalize_call(raw_call.model_dump())
            executed.append({"name": call["name"], "arguments": call["arguments"]})
            if call["arguments"] is None:
                result = {
                    "ok": False,
                    "error": {
                        "code": "invalid_json",
                        "message": "Tool arguments must be valid JSON.",
                    },
                }
            else:
                try:
                    result = tracker.execute(call["name"] or "", call["arguments"] or {})
                except ToolError as exc:
                    result = exc.to_dict()
                except Exception as exc:  # noqa: BLE001
                    result = {"ok": False, "error": {"code": "tool_exception", "message": str(exc)}}
            if not result.get("ok", False):
                tool_errors.append(json.dumps(result.get("error", {})))
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"] or "call",
                    "content": json.dumps(result, ensure_ascii=False),
                }
            )
    else:
        content = content or ""

    passed, errors = score_case(case, executed, content, tracker)
    latency_ms = (time.perf_counter() - started) * 1000
    return {
        "id": case["id"],
        "category": case["category"],
        "passed": passed,
        "errors": errors,
        "latency_ms": round(latency_ms, 1),
        "executed": executed,
        "final_content": content,
        "tool_errors": tool_errors,
    }


def main() -> int:
    args = parse_args()
    client = OpenAI(base_url=args.base_url, api_key=args.api_key)
    cases = [json.loads(line) for line in Path(args.data).read_text().splitlines() if line.strip()]
    results = [run_case(client, args, case) for case in cases]
    totals: Counter[str] = Counter()
    passes: Counter[str] = Counter()
    for result in results:
        totals[result["category"]] += 1
        if result["passed"]:
            passes[result["category"]] += 1

    passed = sum(1 for result in results if result["passed"])
    summary = {
        "model": args.model,
        "data": args.data,
        "total": len(results),
        "passed": passed,
        "rate": passed / len(results) if results else 0.0,
        "p50_latency_ms": sorted(result["latency_ms"] for result in results)[len(results) // 2]
        if results
        else 0.0,
        "categories": {
            category: {
                "total": totals[category],
                "passed": passes[category],
                "rate": passes[category] / totals[category] if totals[category] else 0.0,
            }
            for category in sorted(totals)
        },
        "results": results,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    printable = {
        key: summary[key]
        for key in ("model", "total", "passed", "rate", "p50_latency_ms", "categories")
    }
    print(json.dumps(printable, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
