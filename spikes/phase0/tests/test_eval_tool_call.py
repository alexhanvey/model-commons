from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eval_tool_call import extract_calls, score_case  # noqa: E402

DATA = Path(__file__).resolve().parents[1] / "data" / "hard_heldout_tools.jsonl"
ROWS = {row["id"]: row for row in (json.loads(line) for line in DATA.read_text().splitlines())}


def call(name: str, arguments: dict) -> dict:
    return {"name": name, "arguments": arguments}


class EvalScoringTests(unittest.TestCase):
    def test_single_tool(self) -> None:
        passed, reason = score_case(
            ROWS["h01"],
            [call("get_weather", {"city": "Paris", "unit": "celsius"})],
            "",
        )
        self.assertTrue(passed, reason)

    def test_schema_rejects_bad_arguments(self) -> None:
        passed, _ = score_case(
            ROWS["h01"],
            [call("get_weather", {"city": 123})],
            "",
        )
        self.assertFalse(passed)

    def test_no_tool(self) -> None:
        passed, reason = score_case(ROWS["h09"], [], "Sure, here is a joke.")
        self.assertTrue(passed, reason)

    def test_no_tool_rejects_tool_call(self) -> None:
        passed, _ = score_case(
            ROWS["h09"],
            [call("get_weather", {"city": "Paris"})],
            "",
        )
        self.assertFalse(passed)

    def test_clarify(self) -> None:
        passed, reason = score_case(
            ROWS["h14"],
            [],
            "Which origin, destination, date, and passenger count?",
        )
        self.assertTrue(passed, reason)

    def test_clarify_rejects_tool_call(self) -> None:
        passed, _ = score_case(
            ROWS["h14"],
            [call("book_flight", {"origin": "SFO"})],
            "",
        )
        self.assertFalse(passed)

    def test_multi_tool_order_insensitive(self) -> None:
        passed, reason = score_case(
            ROWS["h19"],
            [
                call("search_docs", {"query": "hotels"}),
                call("get_weather", {"city": "Paris"}),
            ],
            "",
        )
        self.assertTrue(passed, reason)

    def test_multi_tool_missing_call(self) -> None:
        passed, _ = score_case(
            ROWS["h19"],
            [call("get_weather", {"city": "Paris"})],
            "",
        )
        self.assertFalse(passed)

    def test_forbidden_tool(self) -> None:
        passed, _ = score_case(
            ROWS["h29"],
            [call("delete_account", {"user_id": "1"})],
            "",
        )
        self.assertFalse(passed)

    def test_final_answer(self) -> None:
        passed, reason = score_case(ROWS["h34"], [], "It is 18 degrees Celsius in Paris.")
        self.assertTrue(passed, reason)

    def test_extract_content_json(self) -> None:
        message = SimpleNamespace(
            content='{"tool":"get_weather","arguments":{"city":"Paris"}}',
            tool_calls=None,
        )
        calls, source = extract_calls(message)
        self.assertEqual(source, "content_json")
        self.assertEqual(calls[0]["name"], "get_weather")


if __name__ == "__main__":
    unittest.main()
