import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy import engine_from_config
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# 🔹 Import de tes modèles
from app.models import Base  # Assure-toi que Base est bien importé

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# Metadata à utiliser pour autogenerate
target_metadata = Base.metadata

# -------------------------------
# Offline migrations (SQL script)
# -------------------------------
def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


# -------------------------------
# Online migrations (async)
# -------------------------------
def do_run_migrations(connection):
    """Exécuté en sync via connection.run_sync() pour async engine"""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    """Exécute les migrations avec un moteur async"""
    from app.database import DATABASE_URL  # 🔹 Assure-toi que DATABASE_URL est importé
    from sqlalchemy.ext.asyncio import create_async_engine

    connectable = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # ⚡ Exécute les migrations en mode sync à travers run_sync
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# -------------------------------
# Choix mode offline/online
# -------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
