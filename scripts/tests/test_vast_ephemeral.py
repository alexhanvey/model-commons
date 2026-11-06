from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vast_ephemeral import (  # noqa: E402
    BAD_STATES,
    SYNC_EXCLUDES,
    build_offer_query,
    build_parser,
    create_payload,
)


class VastEphemeralTests(unittest.TestCase):
    def test_offer_query_contains_cost_and_vram_limits(self) -> None:
        args = argparse.Namespace(
            gpu_name="RTX 4090",
            min_vram=48000,
            disk=48,
            max_hourly=1.25,
            limit=5,
        )
        query = build_offer_query(args)
        self.assertEqual(query["gpu_name"], {"eq": "RTX 4090"})
        self.assertEqual(query["gpu_ram"], {"gte": 48000})
        self.assertEqual(query["disk_space"], {"gte": 48})
        self.assertEqual(query["dph_total"], {"lte": 1.25})
        self.assertEqual(query["type"], "on-demand")

    def test_create_payload(self) -> None:
        args = argparse.Namespace(
            image="vastai/base-image:@vastai-automatic-tag",
            disk=48,
            label="test",
        )
        payload = create_payload(args)
        self.assertTrue(payload["cancel_unavail"])
        self.assertEqual(payload["runtype"], "ssh")
        self.assertEqual(payload["target_state"], "running")

    def test_bad_states(self) -> None:
        self.assertIn("exited", BAD_STATES)
        self.assertIn("offline", BAD_STATES)

    def test_sync_excludes_secrets_and_bulky_dirs(self) -> None:
        for item in (".env", ".env.*", ".sandbox", ".venv", "node_modules", ".next"):
            with self.subTest(item=item):
                self.assertIn(item, SYNC_EXCLUDES)

    def test_parser_has_lifecycle_commands(self) -> None:
        parser = build_parser()
        for command in ("search", "create", "run", "destroy", "list"):
            with self.subTest(command=command):
                argv = [command, "--instance-id", "1"] if command == "destroy" else [command]
                args = parser.parse_args(argv)
                self.assertEqual(args.command, command)


if __name__ == "__main__":
    unittest.main()
