from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.declarative import DeclarativeMeta
from typing import AsyncGenerator
import os

# -------------------------------
# Variables d'environnement critiques
# -------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL est manquant dans les variables d'environnement")

# -------------------------------
# Moteur asynchrone SQLAlchemy
# -------------------------------
engine = create_async_engine(DATABASE_URL, echo=True)

# -------------------------------
# Fabrique de sessions asynchrones
# -------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# -------------------------------
# Base déclarative pour les modèles
# -------------------------------
Base: DeclarativeMeta = declarative_base()

# -------------------------------
# Fournisseur de session compatible FastAPI
# -------------------------------
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Fournit une session asynchrone pour chaque requête FastAPI.
    Usage : Depends(get_async_session)
    """
    async with AsyncSessionLocal() as session:
        yield session
