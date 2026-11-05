#!/usr/bin/env python3
"""Generate synthetic training data for the issue-tracker tool-use task.

The data is generated from templates and validated against the mock API. It is
not a replacement for human review, but it gives us a controlled first SFT set
with correct tool names, IDs, policies, and multi-step trajectories.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any

from mock_api import MockTracker, ToolError
from schemas import TOOLS

ROOT = Path(__file__).resolve().parent
EVAL_PROMPTS = {
    json.loads(line)["prompt"]
    for line in (ROOT / "eval_cases.jsonl").read_text().splitlines()
    if line.strip()
}
SYSTEM = (
    "You are a cautious issue-tracker assistant. Use only the provided tools. "
    "Never invent issue IDs, project IDs, or user IDs. Ask for missing information. "
    "Ask for explicit confirmation before closing or reopening an issue. "
    "Do not call get_current_user or list_projects unless the user explicitly asks for identity or the project list. "
    "Use the minimum number of tools needed."
)

PROJECTS = {"Atlas": "p_atlas", "Beacon": "p_beacon"}
USERS = {
    "Sam": "u_sam",
    "Maya": "u_maya",
    "Lee": "u_lee",
    "Nina": "u_nina",
    "Ravi": "u_ravi",
    "Alex": "u_alex",
}
PROJECT_USERS = {
    "p_atlas": ["Sam", "Maya", "Lee", "Alex"],
    "p_beacon": ["Nina", "Ravi", "Alex"],
}
OPEN_ISSUES = {
    "p_atlas": [
        "ATLAS-101",
        "ATLAS-102",
        "ATLAS-103",
        "ATLAS-104",
        "ATLAS-105",
        "ATLAS-107",
        "ATLAS-108",
        "ATLAS-109",
    ],
    "p_beacon": ["BEACON-201", "BEACON-202", "BEACON-203", "BEACON-204"],
}
CLOSED_ISSUES = {"p_atlas": ["ATLAS-106"], "p_beacon": []}
LABELS = ["bug", "feature", "docs", "regression", "needs-repro", "duplicate", "good-first-issue"]
PRIORITIES = ["low", "medium", "high", "urgent"]
STYLES = [
    "",
    " Please handle it now.",
    " Keep it concise.",
    " Use the exact IDs from the project.",
    " Do not guess.",
    " This is for today's triage.",
    " Follow the project rules.",
    " Be careful with destructive actions.",
    " Use the tracker tools.",
    " Make the smallest correct change.",
    " Answer briefly.",
    " Use the project names correctly.",
    " Do not make unrelated changes.",
]


def call(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "arguments": arguments}


def build_tool_example(
    prompt: str, steps: list[dict[str, Any]], final_text: str, category: str, index: int
) -> dict[str, Any]:
    tracker = MockTracker()
    tracker.reset()
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ]
    for step_index, step in enumerate(steps):
        try:
            result = tracker.execute(step["name"], step["arguments"])
        except ToolError as exc:
            raise ValueError(f"tool step failed: {step['name']} {exc.code}: {exc.message}") from exc
        call_id = f"call_{index}_{step_index}"
        messages.append(
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": step["name"],
                            "arguments": json.dumps(step["arguments"], ensure_ascii=False),
                        },
                    }
                ],
            }
        )
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call_id,
                "content": json.dumps(result, ensure_ascii=False),
            }
        )
    messages.append({"role": "assistant", "content": final_text})
    return {
        "id": f"issue-train-{index}",
        "category": category,
        "messages": messages,
        "tools": TOOLS,
        "metadata": {"source": "synthetic_issue_tracker", "seed": 7},
    }


def build_text_example(prompt: str, answer: str, category: str, index: int) -> dict[str, Any]:
    return {
        "id": f"issue-train-{index}",
        "category": category,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer},
        ],
        "tools": TOOLS,
        "metadata": {"source": "synthetic_issue_tracker", "seed": 7},
    }


def add_single(
    examples: list[dict[str, Any]], rng: random.Random, target: int, seen: set[str]
) -> None:
    titles = [
        "Login redirect on Firefox",
        "Broken export on mobile",
        "Add CSV date filter",
        "Docs missing webhook secret",
        "Crash when opening large report",
        "Improve empty-state message",
        "Duplicate notification emails",
        "Search result ordering is wrong",
    ]
    while sum(1 for item in examples if item["category"] == "single_tool") < target:
        project_name = rng.choice(["Atlas", "Beacon"])
        project_id = PROJECTS[project_name]
        issue_id = rng.choice(OPEN_ISSUES[project_id])
        user_name = rng.choice(PROJECT_USERS[project_id])
        user_id = USERS[user_name]
        action = rng.choice(
            ["create", "assign", "label", "comment", "search", "get", "close", "reopen", "link"]
        )
        suffix = rng.choice(STYLES)
        if action == "create":
            title = rng.choice(titles)
            priority = rng.choice(PRIORITIES)
            prompt = (
                f"Create a {priority} priority issue in {project_name} titled '{title}'.{suffix}"
            )
            steps = [
                call(
                    "create_issue",
                    {
                        "project_id": project_id,
                        "title": title,
                        "priority": priority,
                        "labels": ["bug"],
                    },
                )
            ]
            answer = f"Created the issue in {project_name}."
        elif action == "assign":
            prompt = f"Assign {issue_id} to {user_name}.{suffix}"
            steps = [call("assign_issue", {"issue_id": issue_id, "assignee_id": user_id})]
            answer = f"Assigned {issue_id} to {user_name}."
        elif action == "label":
            label = rng.choice(LABELS)
            prompt = f"Add the {label} label to {issue_id}.{suffix}"
            steps = [call("add_labels", {"issue_id": issue_id, "labels": [label]})]
            answer = f"Added the {label} label to {issue_id}."
        elif action == "comment":
            body = f"Triaged {issue_id} during the weekly review."
            prompt = f"Comment on {issue_id} with the exact text '{body}'.{suffix}"
            steps = [call("add_comment", {"issue_id": issue_id, "body": body})]
            answer = f"Commented on {issue_id}."
        elif action == "search":
            label = rng.choice(["bug", "feature", "docs", "regression"])
            prompt = f"Search {project_name} for {label} issues, limit 5.{suffix}"
            steps = [call("search_issues", {"project_id": project_id, "label": label, "limit": 5})]
            answer = f"Searched {project_name} for {label} issues."
        elif action == "get":
            prompt = f"Show me the details of {issue_id}.{suffix}"
            steps = [call("get_issue", {"issue_id": issue_id})]
            answer = f"Here are the details for {issue_id}."
        elif action == "close":
            prompt = (
                f"Close {issue_id} with the comment 'Resolved during triage'. I confirm.{suffix}"
            )
            steps = [
                call(
                    "close_issue",
                    {"issue_id": issue_id, "confirm": True, "comment": "Resolved during triage"},
                )
            ]
            answer = f"Closed {issue_id}."
        elif action == "reopen":
            closed = CLOSED_ISSUES[project_id]
            if not closed:
                continue
            issue_id = rng.choice(closed)
            prompt = f"Reopen {issue_id} with the comment 'New report received'. I confirm.{suffix}"
            steps = [
                call(
                    "reopen_issue",
                    {"issue_id": issue_id, "confirm": True, "comment": "New report received"},
                )
            ]
            answer = f"Reopened {issue_id}."
        else:
            other = rng.choice([item for item in OPEN_ISSUES[project_id] if item != issue_id])
            prompt = f"Link {issue_id} to {other} as related.{suffix}"
            steps = [
                call(
                    "link_issues",
                    {"issue_id": issue_id, "linked_issue_id": other, "relationship": "related"},
                )
            ]
            answer = f"Linked {issue_id} and {other}."
        if prompt in seen or prompt in EVAL_PROMPTS:
            continue
        seen.add(prompt)
        examples.append(build_tool_example(prompt, steps, answer, "single_tool", len(examples)))


def add_id_grounding(
    examples: list[dict[str, Any]], rng: random.Random, target: int, seen: set[str]
) -> None:
    while sum(1 for item in examples if item["category"] == "id_grounding") < target:
        project_name = rng.choice(["Atlas", "Beacon"])
        project_id = PROJECTS[project_name]
        issue_id = rng.choice(OPEN_ISSUES[project_id])
        user_name = rng.choice(PROJECT_USERS[project_id])
        user_id = USERS[user_name]
        style = rng.choice(STYLES)
        kind = rng.choice(["search", "assign", "list_users", "comment"])
        if kind == "search":
            prompt = f"In {project_name}, find open bugs assigned to {user_name}, limit 5.{style}"
            steps = [
                call(
                    "search_issues",
                    {
                        "project_id": project_id,
                        "status": "open",
                        "label": "bug",
                        "assignee_id": user_id,
                        "limit": 5,
                    },
                )
            ]
            answer = f"Searched {project_name} for open bugs assigned to {user_name}."
        elif kind == "assign":
            prompt = f"In {project_name}, assign {issue_id} to {user_name}.{style}"
            steps = [call("assign_issue", {"issue_id": issue_id, "assignee_id": user_id})]
            answer = f"Assigned {issue_id} to {user_name} in {project_name}."
        elif kind == "list_users":
            prompt = f"List the users in {project_name}.{style}"
            steps = [call("list_users", {"project_id": project_id})]
            answer = f"Listed the users in {project_name}."
        else:
            body = f"Please review {issue_id} with {user_name}."
            prompt = f"Comment on {issue_id} with the exact text '{body}' and mention {user_name}.{style}"
            steps = [call("add_comment", {"issue_id": issue_id, "body": body})]
            answer = f"Commented on {issue_id} and mentioned {user_name}."
        if prompt in seen or prompt in EVAL_PROMPTS:
            continue
        seen.add(prompt)
        examples.append(build_tool_example(prompt, steps, answer, "id_grounding", len(examples)))


def add_multi(
    examples: list[dict[str, Any]], rng: random.Random, target: int, seen: set[str]
) -> None:
    while sum(1 for item in examples if item["category"] == "multi_tool") < target:
        project_name = rng.choice(["Atlas", "Beacon"])
        project_id = PROJECTS[project_name]
        issue_id = rng.choice(OPEN_ISSUES[project_id])
        user_name = rng.choice(PROJECT_USERS[project_id])
        user_id = USERS[user_name]
        style = rng.choice(STYLES)
        kind = rng.choice(
            [
                "triage",
                "assign_comment",
                "labels_comment",
                "reopen",
                "link",
                "create_assign",
                "search_comment",
            ]
        )
        try:
            if kind == "triage":
                prompt = f"Find open bugs assigned to {user_name} in {project_name}, then add the urgent label to {issue_id} and comment with 'Triage started'.{style}"
                steps = [
                    call(
                        "search_issues",
                        {
                            "project_id": project_id,
                            "status": "open",
                            "label": "bug",
                            "assignee_id": user_id,
                        },
                    ),
                    call("add_labels", {"issue_id": issue_id, "labels": ["urgent"]}),
                    call("add_comment", {"issue_id": issue_id, "body": "Triage started"}),
                ]
                answer = f"Triaged {issue_id} and added a comment."
            elif kind == "assign_comment":
                prompt = f"Show {issue_id}, assign it to {user_name}, and comment with 'Assigned for follow-up'.{style}"
                steps = [
                    call("get_issue", {"issue_id": issue_id}),
                    call("assign_issue", {"issue_id": issue_id, "assignee_id": user_id}),
                    call("add_comment", {"issue_id": issue_id, "body": "Assigned for follow-up"}),
                ]
                answer = f"Assigned {issue_id} to {user_name} and commented."
            elif kind == "labels_comment":
                prompt = f"Get {issue_id}, add the regression label, and comment with 'Regression confirmed'.{style}"
                steps = [
                    call("get_issue", {"issue_id": issue_id}),
                    call("add_labels", {"issue_id": issue_id, "labels": ["regression"]}),
                    call("add_comment", {"issue_id": issue_id, "body": "Regression confirmed"}),
                ]
                answer = f"Added regression context to {issue_id}."
            elif kind == "reopen":
                closed = CLOSED_ISSUES[project_id]
                if not closed:
                    continue
                issue_id = rng.choice(closed)
                prompt = f"Find {issue_id} and reopen it with 'Reopened after new report'. I confirm.{style}"
                steps = [
                    call("get_issue", {"issue_id": issue_id}),
                    call(
                        "reopen_issue",
                        {
                            "issue_id": issue_id,
                            "confirm": True,
                            "comment": "Reopened after new report",
                        },
                    ),
                ]
                answer = f"Reopened {issue_id}."
            elif kind == "link":
                other = rng.choice([item for item in OPEN_ISSUES[project_id] if item != issue_id])
                prompt = f"Get {issue_id} and {other}, then link {issue_id} to {other} as duplicate.{style}"
                steps = [
                    call("get_issue", {"issue_id": issue_id}),
                    call("get_issue", {"issue_id": other}),
                    call(
                        "link_issues",
                        {
                            "issue_id": issue_id,
                            "linked_issue_id": other,
                            "relationship": "duplicate",
                        },
                    ),
                ]
                answer = f"Linked {issue_id} to {other} as duplicate."
            elif kind == "create_assign":
                title = rng.choice(
                    [
                        "Login redirect on Firefox",
                        "Crash on report export",
                        "Missing webhook docs",
                        "Broken mobile layout",
                    ]
                )
                prompt = f"Create a high priority bug in {project_name} titled '{title}', then assign it to {user_name}.{style}"
                steps = [
                    call(
                        "create_issue",
                        {
                            "project_id": project_id,
                            "title": title,
                            "priority": "high",
                            "labels": ["bug"],
                        },
                    ),
                    call(
                        "assign_issue",
                        {
                            "issue_id": ("ATLAS-110" if project_id == "p_atlas" else "BEACON-205"),
                            "assignee_id": user_id,
                        },
                    ),
                ]
                answer = f"Created the issue and assigned it to {user_name}."
            else:
                prompt = f"Search {project_name} for docs issues, then comment on the first one with 'Docs review needed'.{style}"
                steps = [
                    call("search_issues", {"project_id": project_id, "label": "docs"}),
                    call(
                        "add_comment",
                        {
                            "issue_id": ("ATLAS-104" if project_id == "p_atlas" else "BEACON-203"),
                            "body": "Docs review needed",
                        },
                    ),
                ]
                answer = "Searched docs issues and commented."
        except ValueError:
            continue
        if prompt in seen or prompt in EVAL_PROMPTS:
            continue
        seen.add(prompt)
        try:
            example = build_tool_example(prompt, steps, answer, "multi_tool", len(examples))
        except ValueError:
            continue
        examples.append(example)


def add_no_tool(
    examples: list[dict[str, Any]], rng: random.Random, target: int, seen: set[str]
) -> None:
    prompts = [
        "Explain what a regression label means.",
        "Write a polite reply to a customer about a bug.",
        "What is the difference between a bug and a feature?",
        "Draft a short triage checklist.",
        "Summarize why clear issue titles matter.",
        "What should a good bug report include?",
        "Explain the difference between open and in-progress.",
        "Write a short release note about a fixed bug.",
        "What does a duplicate label mean?",
        "How should we prioritize urgent issues?",
    ]
    answers = [
        "This is a general question, so no tracker tool is needed.",
        "That can be answered directly without changing any issue.",
        "No tool call is needed for this writing task.",
        "This is guidance, not a tracker operation.",
        "I can answer this without accessing the project.",
    ]
    while sum(1 for item in examples if item["category"] == "no_tool") < target:
        prompt = rng.choice(prompts) + rng.choice(STYLES)
        if prompt in seen or prompt in EVAL_PROMPTS:
            continue
        seen.add(prompt)
        examples.append(build_text_example(prompt, rng.choice(answers), "no_tool", len(examples)))


def add_clarify(
    examples: list[dict[str, Any]], rng: random.Random, target: int, seen: set[str]
) -> None:
    prompts = [
        "Create an issue.",
        "Assign it to Sam.",
        "Close the issue.",
        "Add a comment.",
        "Set its priority to high.",
        "Remove the bug label.",
        "Link these issues.",
        "Reopen it.",
        "Update it.",
        "Which project should I use?",
        "Move it to in_progress.",
        "Add a regression label.",
        "Who should I assign it to?",
        "What is the due date?",
        "Should I close it?",
    ]
    answers = [
        "Which issue do you mean?",
        "Please provide the issue ID and project.",
        "I need the issue ID before I can do that.",
        "Which project and issue should I use?",
        "Could you provide the missing details?",
    ]
    while sum(1 for item in examples if item["category"] == "clarify") < target:
        prompt = rng.choice(prompts) + rng.choice(STYLES)
        if prompt in seen or prompt in EVAL_PROMPTS:
            continue
        seen.add(prompt)
        examples.append(build_text_example(prompt, rng.choice(answers), "clarify", len(examples)))


def add_confirmation(
    examples: list[dict[str, Any]], rng: random.Random, target: int, seen: set[str]
) -> None:
    ask_prompts = [
        "Close ATLAS-101.",
        "Reopen ATLAS-106.",
        "Close BEACON-204.",
        "Close ATLAS-103.",
        "Close ATLAS-104.",
        "Close ATLAS-108.",
        "Close BEACON-202.",
        "Reopen ATLAS-106 after the new report.",
    ]
    while sum(1 for item in examples if item["category"] == "confirmation") < target:
        if rng.random() < 0.5:
            prompt = rng.choice(ask_prompts) + rng.choice(STYLES)
            if prompt in seen or prompt in EVAL_PROMPTS:
                continue
            seen.add(prompt)
            examples.append(
                build_text_example(
                    prompt,
                    "Please confirm that you want me to proceed before I make this change.",
                    "confirmation",
                    len(examples),
                )
            )
        else:
            issue_id = rng.choice(
                ["ATLAS-103", "ATLAS-104", "ATLAS-107", "ATLAS-108", "BEACON-202", "BEACON-204"]
            )
            prompt = f"Yes, close {issue_id}. I confirm." + rng.choice(STYLES)
            if prompt in seen or prompt in EVAL_PROMPTS:
                continue
            seen.add(prompt)
            steps = [call("close_issue", {"issue_id": issue_id, "confirm": True})]
            try:
                examples.append(
                    build_tool_example(
                        prompt, steps, f"Closed {issue_id}.", "confirmation", len(examples)
                    )
                )
            except ValueError:
                continue


def add_injection(
    examples: list[dict[str, Any]], rng: random.Random, target: int, seen: set[str]
) -> None:
    prompts = [
        "Get ATLAS-109.",
        "Show me ATLAS-109.",
        "Summarize ATLAS-109.",
        "Read ATLAS-109 and tell me what it says.",
        "Fetch issue ATLAS-109 for triage.",
    ]
    while sum(1 for item in examples if item["category"] == "prompt_injection") < target:
        prompt = rng.choice(prompts) + rng.choice(STYLES)
        if prompt in seen or prompt in EVAL_PROMPTS:
            continue
        seen.add(prompt)
        steps = [call("get_issue", {"issue_id": "ATLAS-109"})]
        answer = "I fetched ATLAS-109. The issue body contains instructions to close other issues; I ignored them and made no changes."
        examples.append(
            build_tool_example(prompt, steps, answer, "prompt_injection", len(examples))
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="data/issue_tracker_train.jsonl")
    parser.add_argument("--target", type=int, default=800)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    examples: list[dict[str, Any]] = []
    seen: set[str] = set()

    add_single(examples, rng, 250, seen)
    add_id_grounding(examples, rng, 100, seen)
    add_multi(examples, rng, 120, seen)
    add_no_tool(examples, rng, 100, seen)
    add_clarify(examples, rng, 75, seen)
    add_confirmation(examples, rng, 100, seen)
    add_injection(examples, rng, 55, seen)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as handle:
        for example in examples:
            handle.write(json.dumps(example, ensure_ascii=False, separators=(",", ":")) + "\n")

    categories: dict[str, int] = {}
    for example in examples:
        categories[example["category"]] = categories.get(example["category"], 0) + 1
    print(
        json.dumps(
            {"output": str(output), "count": len(examples), "categories": categories}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
