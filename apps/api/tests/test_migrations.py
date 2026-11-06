from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

TEST_DATABASE_URL = os.getenv("COMMUNITY_LLM_TEST_DATABASE_URL", "")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="COMMUNITY_LLM_TEST_DATABASE_URL is not set",
)


def _alembic_config() -> Config:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", TEST_DATABASE_URL)
    return config


async def _table_names() -> list[str]:
    engine = create_async_engine(TEST_DATABASE_URL)
    try:
        async with engine.connect() as connection:
            return await connection.run_sync(
                lambda sync_connection: inspect(sync_connection).get_table_names()
            )
    finally:
        await engine.dispose()


def test_migrations_upgrade_and_downgrade() -> None:
    config = _alembic_config()

    command.upgrade(config, "head")
    tables = asyncio.run(_table_names())
    assert "users" in tables
    assert "sessions" in tables

    command.downgrade(config, "base")
    tables = asyncio.run(_table_names())
    assert "users" not in tables
    assert "sessions" not in tables

    command.upgrade(config, "head")
    tables = asyncio.run(_table_names())
    assert "users" in tables
    assert "sessions" in tables
