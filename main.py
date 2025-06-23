import os
import asyncio
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.routers import welcom  # 👈 import du nouveau routeur
from app.routers import quotidien

from app.database import Base
from app.routers import (
    auth,
    user,
    balance,
    level,
    ranking,
    tasks,
    friends,
    wallet,
    actions,
    status,
    myactions,
)

# 🔄 Chargement des variables d’environnement
load_dotenv()

# 🔑 Récupération de l'URL de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ La variable DATABASE_URL est manquante dans le fichier .env")

# ✅ Adaptation pour un moteur async
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ⚙️ Moteur SQLAlchemy async
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# 📌 Création asynchrone des tables
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 🚀 Initialisation FastAPI
app = FastAPI(
    title="BlackCoin API",
    description="Backend for managing user data, profiles, and activities",
    version="1.0.0",
)

# 🌍 Middleware CORS
origins = ["https://blackcoin-v5-frontend.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🧩 Inclusion des routers
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
app.include_router(auth.router)  # déjà taggé avec /auth dans le router lui-même
app.include_router(quotidien.router)
app.include_router(welcom.router, prefix="/welcome", tags=["Welcome"])  # ✅ ajouté ici

# 🔗 Endpoint racine
@app.get("/")
async def read_root():
    return {"message": "Welcome to the BlackCoin API!"}

# 🚀 Création des tables à l'initialisation
@app.on_event("startup")
async def on_startup():
    await init_models()
