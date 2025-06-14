import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

# 🔄 Chargement des variables d'environnement
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans le fichier .env")

# 🔁 Adaptation de l’URL si nécessaire
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ⚙️ Création de l'engine asynchrone
engine = create_async_engine(DATABASE_URL, echo=True)

# 🧵 Création de la session asynchrone
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)

# 🏗️ Base des modèles
class Base(DeclarativeBase):
    pass

# 🔌 Dépendance FastAPI pour injecter une session DB
@asynccontextmanager
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
