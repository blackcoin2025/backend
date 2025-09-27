# app/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from dotenv import load_dotenv
from typing import AsyncGenerator
import os

# 🔄 Charge les variables d'environnement
load_dotenv()

# 🛠️ URL de connexion à la base PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans .env")

# 🔌 Moteur asynchrone SQLAlchemy avec gestion du pool
engine = create_async_engine(
    DATABASE_URL,
    echo=True,            # 🔍 Debug SQL (désactive en prod)
    pool_size=10,         # connexions persistantes
    max_overflow=20,      # connexions temporaires en cas de charge
    pool_timeout=30,      # délai max avant "timeout"
    pool_recycle=1800,    # recycle après 30 min (évite connexions mortes)
    pool_pre_ping=True,   # vérifie la connexion avant usage
)

# 🏭 Fabrique de sessions async
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 📦 Base déclarative pour les modèles SQLAlchemy
Base: DeclarativeMeta = declarative_base()

# ✅ Fournisseur de session (pour FastAPI Depends)
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
