"""Alembic migration environment for HYBRID Monitor Phoenix."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from hybrid_monitor.core.settings import get_settings
from hybrid_monitor.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


async def run_migrations_online() -> None:
    """Run migrations using the asynchronous SQLAlchemy engine."""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_connection: context.configure(
                connection=sync_connection,
                target_metadata=target_metadata,
            )
        )

        await connection.run_sync(lambda _: context.run_migrations())

    await connectable.dispose()


import asyncio

asyncio.run(run_migrations_online())
