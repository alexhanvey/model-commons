"""Deterministic mock issue tracker for the Phase 0 domain eval."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from schemas import LABELS, PRIORITY, STATUS

FIXTURES = Path(__file__).with_name("fixtures.json")


class ToolError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"ok": False, "error": {"code": self.code, "message": self.message}}


class MockTracker:
    def __init__(self, fixtures: Path | str = FIXTURES) -> None:
        self._fixtures = json.loads(Path(fixtures).read_text())
        self.reset()

    def reset(self) -> None:
        self.state = copy.deepcopy(self._fixtures)
        self.current_user_id = self.state["current_user_id"]

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def _user(self, user_id: str | None) -> dict[str, Any]:
        if user_id is None:
            raise ToolError("invalid_user", "A user ID is required.")
        for user in self.state["users"]:
            if user["id"] == user_id:
                return user
        raise ToolError("unknown_user", f"Unknown user: {user_id}")

    def _project(self, project_id: str | None) -> dict[str, Any]:
        if not project_id:
            raise ToolError("missing_project", "A project ID is required.")
        for project in self.state["projects"]:
            if project["id"] == project_id:
                return project
        raise ToolError("unknown_project", f"Unknown project: {project_id}")

    def _issue(self, issue_id: str | None) -> dict[str, Any]:
        if not issue_id:
            raise ToolError("missing_issue", "An issue ID is required.")
        for issue in self.state["issues"]:
            if issue["id"] == issue_id:
                return issue
        raise ToolError("unknown_issue", f"Unknown issue: {issue_id}")

    def _current_user(self) -> dict[str, Any]:
        return self._user(self.current_user_id)

    def _can_access_project(self, project_id: str) -> None:
        project = self._project(project_id)
        if self.current_user_id not in project["member_ids"]:
            raise ToolError("forbidden", f"The current user cannot access project {project_id}.")

    def _can_access_issue(self, issue: dict[str, Any]) -> None:
        self._can_access_project(issue["project_id"])

    def _check_labels(self, labels: list[str]) -> None:
        unknown = [label for label in labels if label not in LABELS]
        if unknown:
            raise ToolError("unknown_label", f"Unknown labels: {unknown}")
        if any(label not in LABELS for label in labels):
            raise ToolError("unknown_label", "Unknown label.")

    def _check_assignee(self, project: dict[str, Any], assignee_id: str | None) -> None:
        if assignee_id is None:
            return
        self._user(assignee_id)
        if assignee_id not in project["member_ids"]:
            raise ToolError(
                "invalid_assignee", f"{assignee_id} is not a member of {project['id']}."
            )

    def _touch(self, issue: dict[str, Any], timestamp: str = "2026-11-03T20:00:00Z") -> None:
        issue["updated_at"] = timestamp

    def get_current_user(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "user": self._current_user()}

    def list_projects(self, arguments: dict[str, Any]) -> dict[str, Any]:
        projects = [
            project
            for project in self.state["projects"]
            if self.current_user_id in project["member_ids"]
        ]
        return {"ok": True, "projects": projects}

    def list_users(self, arguments: dict[str, Any]) -> dict[str, Any]:
        project_id = arguments.get("project_id")
        if project_id:
            self._can_access_project(project_id)
            project = self._project(project_id)
            users = [user for user in self.state["users"] if user["id"] in project["member_ids"]]
        else:
            users = self.state["users"]
        return {"ok": True, "users": users}

    def search_issues(self, arguments: dict[str, Any]) -> dict[str, Any]:
        project_id = arguments.get("project_id")
        if project_id:
            self._can_access_project(project_id)
        status = arguments.get("status")
        label = arguments.get("label")
        assignee_id = arguments.get("assignee_id")
        priority = arguments.get("priority")
        text = (arguments.get("text") or "").lower()
        limit = int(arguments.get("limit") or 20)

        if status and status not in STATUS:
            raise ToolError("invalid_status", f"Unknown status: {status}")
        if priority and priority not in PRIORITY:
            raise ToolError("invalid_priority", f"Unknown priority: {priority}")
        if label and label not in LABELS:
            raise ToolError("unknown_label", f"Unknown label: {label}")

        results = []
        for issue in self.state["issues"]:
            if self.current_user_id not in self._project(issue["project_id"])["member_ids"]:
                continue
            if project_id and issue["project_id"] != project_id:
                continue
            if status and issue["status"] != status:
                continue
            if label and label not in issue["labels"]:
                continue
            if assignee_id is not None and issue["assignee_id"] != assignee_id:
                continue
            if priority and issue["priority"] != priority:
                continue
            if text and text not in (issue["title"] + " " + issue["body"]).lower():
                continue
            results.append(issue)

        results.sort(key=lambda item: item["created_at"])
        return {"ok": True, "issues": results[:limit], "count": len(results)}

    def get_issue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        return {"ok": True, "issue": issue}

    def create_issue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        project = self._project(arguments.get("project_id"))
        self._can_access_project(project["id"])
        title = (arguments.get("title") or "").strip()
        if not title:
            raise ToolError("missing_title", "An issue title is required.")
        labels = arguments.get("labels") or []
        self._check_labels(labels)
        assignee_id = arguments.get("assignee_id")
        self._check_assignee(project, assignee_id)
        priority = arguments.get("priority") or "medium"
        if priority not in PRIORITY:
            raise ToolError("invalid_priority", f"Unknown priority: {priority}")

        number = max(
            [
                int(issue["id"].split("-")[-1])
                for issue in self.state["issues"]
                if issue["project_id"] == project["id"]
            ]
            or [100]
        )
        issue = {
            "id": f"{project['key']}-{number + 1}",
            "project_id": project["id"],
            "title": title,
            "body": arguments.get("body") or "",
            "status": "open",
            "priority": priority,
            "assignee_id": assignee_id,
            "labels": sorted(set(labels)),
            "created_at": "2026-11-03T20:00:00Z",
            "updated_at": "2026-11-03T20:00:00Z",
            "comments": [],
            "linked_issues": [],
        }
        self.state["issues"].append(issue)
        return {"ok": True, "issue": issue}

    def update_issue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        if issue["status"] == "closed":
            raise ToolError("issue_closed", "Closed issues must be reopened before editing.")
        if "status" in arguments and arguments["status"] == "closed":
            raise ToolError("use_close_issue", "Use close_issue to close an issue.")
        if "status" in arguments and arguments["status"] not in STATUS:
            raise ToolError("invalid_status", f"Unknown status: {arguments['status']}")
        if "priority" in arguments and arguments["priority"] not in PRIORITY:
            raise ToolError("invalid_priority", f"Unknown priority: {arguments['priority']}")
        for field in ("title", "body", "status", "priority"):
            if field in arguments:
                issue[field] = arguments[field]
        self._touch(issue)
        return {"ok": True, "issue": issue}

    def assign_issue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        if issue["status"] == "closed":
            raise ToolError("issue_closed", "Closed issues must be reopened before editing.")
        project = self._project(issue["project_id"])
        assignee_id = arguments.get("assignee_id")
        self._check_assignee(project, assignee_id)
        issue["assignee_id"] = assignee_id
        self._touch(issue)
        return {"ok": True, "issue": issue}

    def add_labels(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        if issue["status"] == "closed":
            raise ToolError("issue_closed", "Closed issues must be reopened before editing.")
        labels = arguments.get("labels") or []
        self._check_labels(labels)
        issue["labels"] = sorted(set(issue["labels"] + labels))
        self._touch(issue)
        return {"ok": True, "issue": issue}

    def remove_label(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        if issue["status"] == "closed":
            raise ToolError("issue_closed", "Closed issues must be reopened before editing.")
        label = arguments.get("label")
        if label not in LABELS:
            raise ToolError("unknown_label", f"Unknown label: {label}")
        issue["labels"] = [item for item in issue["labels"] if item != label]
        self._touch(issue)
        return {"ok": True, "issue": issue}

    def add_comment(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        body = (arguments.get("body") or "").strip()
        if not body:
            raise ToolError("missing_body", "A comment body is required.")
        comment = {
            "author_id": self.current_user_id,
            "body": body,
            "created_at": "2026-11-03T20:00:00Z",
        }
        issue["comments"].append(comment)
        self._touch(issue)
        return {"ok": True, "issue": issue, "comment": comment}

    def link_issues(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        linked = self._issue(arguments.get("linked_issue_id"))
        self._can_access_issue(issue)
        self._can_access_issue(linked)
        if issue["id"] == linked["id"]:
            raise ToolError("invalid_link", "An issue cannot link to itself.")
        if issue["project_id"] != linked["project_id"]:
            raise ToolError("invalid_link", "Issues must be in the same project.")
        if linked["id"] not in issue["linked_issues"]:
            issue["linked_issues"].append(linked["id"])
        if issue["id"] not in linked["linked_issues"]:
            linked["linked_issues"].append(issue["id"])
        self._touch(issue)
        self._touch(linked)
        return {"ok": True, "issue": issue, "linked_issue": linked}

    def close_issue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        if arguments.get("confirm") is not True:
            raise ToolError(
                "confirmation_required", "Refusing to close without explicit confirmation."
            )
        if issue["status"] == "closed":
            raise ToolError("already_closed", "The issue is already closed.")
        issue["status"] = "closed"
        if arguments.get("comment"):
            issue["comments"].append(
                {
                    "author_id": self.current_user_id,
                    "body": arguments["comment"],
                    "created_at": "2026-11-03T20:00:00Z",
                }
            )
        self._touch(issue)
        return {"ok": True, "issue": issue}

    def reopen_issue(self, arguments: dict[str, Any]) -> dict[str, Any]:
        issue = self._issue(arguments.get("issue_id"))
        self._can_access_issue(issue)
        if arguments.get("confirm") is not True:
            raise ToolError(
                "confirmation_required", "Refusing to reopen without explicit confirmation."
            )
        if issue["status"] != "closed":
            raise ToolError("not_closed", "The issue is not closed.")
        issue["status"] = "open"
        if arguments.get("comment"):
            issue["comments"].append(
                {
                    "author_id": self.current_user_id,
                    "body": arguments["comment"],
                    "created_at": "2026-11-03T20:00:00Z",
                }
            )
        self._touch(issue)
        return {"ok": True, "issue": issue}

    def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        method = getattr(self, name, None)
        if method is None:
            raise ToolError("unknown_tool", f"Unknown tool: {name}")
        return method(arguments)
