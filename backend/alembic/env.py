from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
import os

# ── Make app importable from alembic/ directory ───────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine
from app.models import Base          # ← imports ALL models via __init__.py
from app.config import settings

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Point Alembic at our models' metadata ────────────────────────────────────
# This is how Alembic knows what tables exist.
# When you run 'alembic revision --autogenerate', it compares
# Base.metadata (what your models define) against the actual DB schema
# and generates the difference as a migration.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Useful for generating SQL scripts to review before applying.
    """
    url = settings.DATABASE_URL
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations with a live DB connection.
    This is what 'alembic upgrade head' uses.
    """
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


# Run offline or online based on how Alembic was invoked
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()