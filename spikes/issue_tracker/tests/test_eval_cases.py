from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eval_harness import score_case  # noqa: E402
from mock_api import MockTracker  # noqa: E402


class EvalCaseConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cases = [
            json.loads(line)
            for line in (ROOT / "eval_cases.jsonl").read_text().splitlines()
            if line.strip()
        ]

    def test_all_cases_pass_with_expected_behavior(self) -> None:
        for case in self.cases:
            with self.subTest(case=case["id"]):
                tracker = MockTracker()
                tracker.reset()
                kind = case["expected"].get("type", "tool_call")

                if kind == "tool_call":
                    executed = []
                    for expected_call in case["expected"]["calls"]:
                        result = tracker.execute(expected_call["name"], expected_call["arguments"])
                        self.assertTrue(result.get("ok"), result)
                        executed.append(expected_call)
                    passed, errors = score_case(case, executed, "", tracker)
                elif kind == "no_tool":
                    passed, errors = score_case(case, [], "Here is a direct answer.", tracker)
                elif kind == "clarify":
                    passed, errors = score_case(
                        case, [], "Which issue and project do you mean?", tracker
                    )
                elif kind == "final_answer":
                    passed, errors = score_case(
                        case, [], "The issue is closed; reopen it first.", tracker
                    )
                else:
                    self.fail(f"unknown expected type: {kind}")

                self.assertTrue(passed, errors)

    def test_case_count_and_categories(self) -> None:
        self.assertEqual(len(self.cases), 60)
        categories = {case["category"] for case in self.cases}
        self.assertEqual(
            categories,
            {
                "single_tool",
                "multi_tool",
                "clarify",
                "no_tool",
                "nested_search",
                "confirmation",
                "prompt_injection",
            },
        )


if __name__ == "__main__":
    unittest.main()
