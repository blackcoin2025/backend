# main.py

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.routers import telegram as auth  # ⚠️ important : alias

# 🔄 Charger .env
load_dotenv()

# 📦 DB config
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans .env")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# 🔌 SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_='AsyncSession', expire_on_commit=False)

# 🛠 Création des tables
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# 🚀 Init FastAPI
app = FastAPI(
    title="BlackCoin Auth API",
    description="API d'authentification via Telegram",
    version="1.0.0",
)

# 🌍 CORS
origins = [
    "https://blackcoin-v5-frontend.vercel.app",
    "https://staging-blackcoin.vercel.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔗 Routeur unique : Auth
app.include_router(auth.router)

# ✅ Healthcheck
@app.get("/")
async def root():
    return {"message": "API d'authentification prête."}

# 🛡 Middleware global d’erreur
@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"message": "Erreur serveur inattendue", "details": str(exc)},
        )

# 📅 Créer les tables à l'init
@app.on_event("startup")
async def on_startup():
    await init_models()
