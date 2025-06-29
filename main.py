import os
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import UserProfile
from app.routers import telegram as auth

# ✅ Chargement des variables d'environnement
load_dotenv()

# ✅ Configuration de la base de données
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans .env")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ✅ Initialisation de SQLAlchemy async
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# ✅ Création des tables au démarrage
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("📦 Tables créées :", list(Base.metadata.tables.keys()))

# ✅ Instance FastAPI
app = FastAPI(
    title="BlackCoin Auth API",
    description="API d'authentification via Telegram",
    version="1.0.0",
)

# ✅ Middleware CORS
origins = [
    "http://localhost:5173",
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

# ✅ Middleware global pour attraper les erreurs serveur avec traceback
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        traceback_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        print("🔴 Traceback erreur :\n", traceback_str)
        return JSONResponse(
            status_code=500,
            content={"message": "Erreur serveur inattendue", "details": str(exc)},
        )

# ✅ Gestion propre des erreurs de validation (422)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

# ✅ Endpoint de test simple
@app.get("/")
async def root():
    return {"message": "API d'authentification prête."}

# ✅ Inclusion des routes Telegram
app.include_router(auth.router)

# ✅ Démarrage : création automatique des tables
@app.on_event("startup")
async def on_startup():
    await init_models()
