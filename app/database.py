# app/database.py

import os
from typing import AsyncGenerator
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta

# -----------------------
# ENV
# -----------------------
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans .env")

ENV = os.getenv("ENV", "dev")  # dev | prod

# -----------------------
# ENGINE (OPTIMISÉ)
# -----------------------
engine = create_async_engine(
    DATABASE_URL,

    # ✅ SQL logs seulement en dev
    echo=(ENV == "dev"),

    # ✅ Pool adapté petit serveur (Render)
    pool_size=5,
    max_overflow=5,

    # ✅ Timeout plus réactif
    pool_timeout=10,

    # ✅ évite connexions mortes
    pool_recycle=1800,
    pool_pre_ping=True,
)

# -----------------------
# SESSION
# -----------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -----------------------
# BASE MODELS
# -----------------------
Base: DeclarativeMeta = declarative_base()

# -----------------------
# DEPENDENCY FASTAPI
# -----------------------
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session