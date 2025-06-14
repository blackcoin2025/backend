import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.routers import telegram

from app.database import Base
from app.routers import (
    user,
    balance,
    level,
    ranking,
    tasks,
    friends,
    wallet,
    actions,
    status,
    myactions  # Corrigé ici
)

# 🔄 Chargement des variables d’environnement depuis .env
load_dotenv()

# ✅ Récupération de l’URL de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("❌ La variable d’environnement DATABASE_URL est manquante dans le fichier .env")

# 📦 Initialisation du moteur SQLAlchemy
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 📌 Création des tables si elles n’existent pas
Base.metadata.create_all(bind=engine)

# 🚀 Initialisation de l’application FastAPI
app = FastAPI(
    title="BlackCoin API",
    description="Backend for managing user data, profiles, and activities",
    version="1.0.0",
)

# 🌍 Configuration CORS (⚠️ à restreindre en prod)
origins = ["https://blackcoin-v5-frontend.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧩 Inclusion des routers (modulaires et propres)
app.include_router(user.router, prefix="/user", tags=["User"])
app.include_router(balance.router, prefix="/balance", tags=["Balance"])
app.include_router(level.router, prefix="/level", tags=["Level"])
app.include_router(ranking.router, prefix="/ranking", tags=["Ranking"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])
app.include_router(friends.router, prefix="/friends", tags=["Friends"])
app.include_router(wallet.router, prefix="/wallet", tags=["Wallet"])
app.include_router(actions.router, prefix="/actions", tags=["Actions"])
app.include_router(status.router, prefix="/status", tags=["Status"])
app.include_router(myactions.router, prefix="/myactions", tags=["MyActions"])
app.include_router(telegram.router, prefix="/telegram", tags=["Telegram"])

# 🔗 Endpoint racine
@app.get("/")
def read_root():
    return {"message": "Welcome to the BlackCoin API!"}
