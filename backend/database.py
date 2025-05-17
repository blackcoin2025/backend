from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Charger les variables d'environnement depuis le fichier .env
load_dotenv()

# Récupérer l'URL de connexion PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

# Vérification si la variable est bien définie
if not DATABASE_URL:
    raise ValueError("❌ La variable d'environnement DATABASE_URL est introuvable. Vérifie ton fichier .env")

# Création de l'engine async SQLAlchemy avec SSL pour Neon
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"ssl": "require"}  # Obligatoire pour Neon
)

# Sessionmaker pour les sessions de base de données async
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base pour les modèles SQLAlchemy
Base = declarative_base()

# Dépendance pour les routes FastAPI
async def get_db():
    async with async_session() as session:
        yield session
