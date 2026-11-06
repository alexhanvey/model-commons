#!/usr/bin/env python3
"""Check ledger invariants and print a JSON report."""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict

from community_llm_api.db import dispose_engine, get_sessionmaker
from community_llm_api.ledger import reconcile_ledger


async def main() -> int:
    try:
        async with get_sessionmaker()() as session:
            result = await reconcile_ledger(session)
        print(json.dumps(asdict(result), indent=2, sort_keys=True))
        return 0 if result.ok else 1
    finally:
        await dispose_engine()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
