import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import UserProfile
print("✅ Modèle UserProfile importé : ", UserProfile.__tablename__)
from app.routers import telegram as auth


# Charger les variables d'environnement
load_dotenv()

# Config base de données
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("❌ DATABASE_URL manquant dans .env")

if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Config SQLAlchemy
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Fonction d'initialisation des tables
async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        tables = Base.metadata.tables.keys()
        print("📦 Tables détectées par SQLAlchemy :", list(tables))

# Création de l'app FastAPI
app = FastAPI(
    title="BlackCoin Auth API",
    description="API d'authentification via Telegram",
    version="1.0.0",
)

# Middleware CORS
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

# Inclusion du routeur Telegram (auth)
app.include_router(auth.router)

# Endpoint Healthcheck
@app.get("/")
async def root():
    return {"message": "API d'authentification prête."}

# Middleware global de gestion des erreurs
@app.middleware("http")
async def catch_exceptions_middleware(request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={"message": "Erreur serveur inattendue", "details": str(exc)},
        )

# Création des tables au démarrage de l'app
@app.on_event("startup")
async def on_startup():
    await init_models()
