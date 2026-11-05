from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TrainingDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rows = [
            json.loads(line)
            for line in (ROOT / "data" / "issue_tracker_train_v2.jsonl").read_text().splitlines()
            if line.strip()
        ]
        self.eval_prompts = {
            json.loads(line)["prompt"]
            for line in (ROOT / "eval_cases.jsonl").read_text().splitlines()
            if line.strip()
        }

    def test_count_and_categories(self) -> None:
        self.assertEqual(len(self.rows), 800)
        counts = Counter(row["category"] for row in self.rows)
        self.assertEqual(
            counts,
            {
                "single_tool": 250,
                "id_grounding": 100,
                "multi_tool": 120,
                "no_tool": 100,
                "clarify": 75,
                "confirmation": 100,
                "prompt_injection": 55,
            },
        )

    def test_unique_prompts_and_no_eval_overlap(self) -> None:
        prompts = [row["messages"][1]["content"] for row in self.rows]
        self.assertEqual(len(prompts), len(set(prompts)))
        overlap = set(prompts) & self.eval_prompts
        self.assertFalse(overlap, overlap)

    def test_message_shapes(self) -> None:
        for row in self.rows:
            messages = row["messages"]
            self.assertEqual(messages[0]["role"], "system")
            self.assertEqual(messages[1]["role"], "user")
            self.assertEqual(messages[-1]["role"], "assistant")
            self.assertTrue(row["tools"])
            assistant_call_ids = set()
            tool_ids = set()
            for message in messages:
                if message["role"] == "assistant" and message.get("tool_calls"):
                    for call in message["tool_calls"]:
                        self.assertEqual(call["type"], "function")
                        self.assertTrue(call["function"]["name"])
                        json.loads(call["function"]["arguments"])
                        assistant_call_ids.add(call["id"])
                if message["role"] == "tool":
                    tool_ids.add(message["tool_call_id"])
            self.assertEqual(assistant_call_ids, tool_ids)

    def test_policy_examples(self) -> None:
        no_tool = [row for row in self.rows if row["category"] == "no_tool"]
        clarify = [row for row in self.rows if row["category"] == "clarify"]
        confirmation = [row for row in self.rows if row["category"] == "confirmation"]
        self.assertTrue(clarify)
        self.assertTrue(
            all(not any(m.get("tool_calls") for m in row["messages"]) for row in no_tool)
        )
        self.assertTrue(
            any("confirm" in row["messages"][-1]["content"].lower() for row in confirmation)
        )


if __name__ == "__main__":
    unittest.main()
