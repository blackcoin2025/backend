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

# 🔌 Crée le moteur asynchrone SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)

# 🏭 Crée une fabrique de sessions async
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 📦 Base déclarative pour les modèles SQLAlchemy
Base: DeclarativeMeta = declarative_base()

# ✅ Fournisseur de session compatible FastAPI
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
