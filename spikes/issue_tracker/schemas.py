"""Tool schemas for the issue-tracker assistant."""

from __future__ import annotations

from typing import Any

STATUS = ["open", "in_progress", "closed"]
PRIORITY = ["low", "medium", "high", "urgent"]
LABELS = [
    "bug",
    "feature",
    "docs",
    "regression",
    "needs-repro",
    "duplicate",
    "urgent",
    "good-first-issue",
]


def tool(
    name: str, description: str, properties: dict[str, Any], required: list[str] | None = None
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
                "additionalProperties": False,
            },
        },
    }


TOOLS: list[dict[str, Any]] = [
    tool("get_current_user", "Return the current authenticated user.", {}),
    tool(
        "list_projects",
        "List projects visible to the current user.",
        {},
    ),
    tool(
        "list_users",
        "List users, optionally limited to a project.",
        {"project_id": {"type": "string", "description": "Project ID such as p_atlas."}},
    ),
    tool(
        "search_issues",
        "Search issues by project, status, label, assignee, priority, or text.",
        {
            "project_id": {"type": "string"},
            "status": {"type": "string", "enum": STATUS},
            "label": {"type": "string", "enum": LABELS},
            "assignee_id": {"type": "string"},
            "priority": {"type": "string", "enum": PRIORITY},
            "text": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 20},
        },
    ),
    tool(
        "get_issue",
        "Fetch one issue by ID.",
        {"issue_id": {"type": "string", "description": "Issue ID such as ATLAS-101."}},
        ["issue_id"],
    ),
    tool(
        "create_issue",
        "Create an issue in a project.",
        {
            "project_id": {"type": "string"},
            "title": {"type": "string"},
            "body": {"type": "string"},
            "priority": {"type": "string", "enum": PRIORITY},
            "labels": {"type": "array", "items": {"type": "string", "enum": LABELS}},
            "assignee_id": {"type": "string"},
        },
        ["project_id", "title"],
    ),
    tool(
        "update_issue",
        "Update an issue title, body, status, or priority. Closed issues must be reopened first.",
        {
            "issue_id": {"type": "string"},
            "title": {"type": "string"},
            "body": {"type": "string"},
            "status": {"type": "string", "enum": STATUS},
            "priority": {"type": "string", "enum": PRIORITY},
        },
        ["issue_id"],
    ),
    tool(
        "assign_issue",
        "Assign or unassign an issue. Assignees must be project members.",
        {
            "issue_id": {"type": "string"},
            "assignee_id": {
                "type": ["string", "null"],
                "description": "User ID, or null to unassign.",
            },
        },
        ["issue_id", "assignee_id"],
    ),
    tool(
        "add_labels",
        "Add one or more labels to an issue.",
        {
            "issue_id": {"type": "string"},
            "labels": {"type": "array", "items": {"type": "string", "enum": LABELS}, "minItems": 1},
        },
        ["issue_id", "labels"],
    ),
    tool(
        "remove_label",
        "Remove one label from an issue.",
        {
            "issue_id": {"type": "string"},
            "label": {"type": "string", "enum": LABELS},
        },
        ["issue_id", "label"],
    ),
    tool(
        "add_comment",
        "Add a comment to an issue.",
        {
            "issue_id": {"type": "string"},
            "body": {"type": "string"},
        },
        ["issue_id", "body"],
    ),
    tool(
        "link_issues",
        "Link an issue to another issue in the same project.",
        {
            "issue_id": {"type": "string"},
            "linked_issue_id": {"type": "string"},
            "relationship": {
                "type": "string",
                "enum": ["related", "duplicate"],
                "default": "related",
            },
        },
        ["issue_id", "linked_issue_id"],
    ),
    tool(
        "close_issue",
        "Close an issue. Requires explicit confirmation.",
        {
            "issue_id": {"type": "string"},
            "comment": {"type": "string"},
            "confirm": {
                "type": "boolean",
                "description": "Must be true only after the user explicitly confirms.",
            },
        },
        ["issue_id", "confirm"],
    ),
    tool(
        "reopen_issue",
        "Reopen a closed issue. Requires explicit confirmation.",
        {
            "issue_id": {"type": "string"},
            "comment": {"type": "string"},
            "confirm": {
                "type": "boolean",
                "description": "Must be true only after the user explicitly confirms.",
            },
        },
        ["issue_id", "confirm"],
    ),
]


def tool_schema(name: str) -> dict[str, Any] | None:
    for item in TOOLS:
        if item["function"]["name"] == name:
            return item["function"]["parameters"]
    return None
