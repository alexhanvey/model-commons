from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mock_api import MockTracker, ToolError  # noqa: E402


class MockTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = MockTracker()
        self.tracker.reset()

    def test_create_issue_gets_next_id(self) -> None:
        result = self.tracker.create_issue(
            {"project_id": "p_atlas", "title": "New bug", "priority": "high", "labels": ["bug"]}
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["issue"]["id"], "ATLAS-110")

    def test_assign_to_non_member_fails(self) -> None:
        with self.assertRaises(ToolError):
            self.tracker.assign_issue({"issue_id": "ATLAS-103", "assignee_id": "u_grace"})

    def test_close_requires_confirmation(self) -> None:
        with self.assertRaises(ToolError) as context:
            self.tracker.close_issue({"issue_id": "ATLAS-103", "confirm": False})
        self.assertEqual(context.exception.code, "confirmation_required")

    def test_close_and_reopen(self) -> None:
        closed = self.tracker.close_issue({"issue_id": "ATLAS-103", "confirm": True})
        self.assertEqual(closed["issue"]["status"], "closed")
        reopened = self.tracker.reopen_issue({"issue_id": "ATLAS-103", "confirm": True})
        self.assertEqual(reopened["issue"]["status"], "open")

    def test_cannot_edit_closed_issue(self) -> None:
        with self.assertRaises(ToolError) as context:
            self.tracker.update_issue({"issue_id": "ATLAS-106", "priority": "high"})
        self.assertEqual(context.exception.code, "issue_closed")

    def test_search_filters(self) -> None:
        result = self.tracker.search_issues(
            {"project_id": "p_atlas", "status": "open", "label": "bug", "assignee_id": "u_alex"}
        )
        ids = [issue["id"] for issue in result["issues"]]
        self.assertEqual(ids, ["ATLAS-101", "ATLAS-108"])


if __name__ == "__main__":
    unittest.main()
