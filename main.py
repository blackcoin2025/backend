from dotenv import load_dotenv
load_dotenv()

import logging
import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from hashlib import sha256
import hmac

from app.database import engine, Base, AsyncSessionLocal
from app.services.addtasks import add_sample_tasks
from app.routes import welcome, wallet, balance, user_profile, mining, minhistory, tasks
from app.routers import auth, auth_login, friends

# -----------------------
# Configuration des logs
# -----------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("uvicorn.error")

# -----------------------
# Configuration de l'environnement
# -----------------------
ENVIRONMENT = os.getenv("BACKEND_ENV", "development").lower()
IS_PROD = ENVIRONMENT == "production"

# Sources autorisées
ALLOWED_SOURCES = ["telegram", "my_app"]

# -----------------------
# Création de l'application FastAPI
# -----------------------
app = FastAPI(
    title="BlackCoin API",
    description="Backend API pour l'application BlackCoin",
    version="1.0.0"
)

# -----------------------
# Configuration CORS
# -----------------------
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "https://blackcoin-v5-frontend.vercel.app",
    "https://t.me",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Vérification Telegram initData
# -----------------------
def verify_telegram_init_data(init_data: str) -> bool:
    """
    Vérifie l'authenticité du initData Telegram WebApp.
    ⚠️ Doit correspondre à ton bot token côté serveur.
    """
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.error("Telegram bot token manquant")
        return False

    # Telegram envoie initData sous forme de query string
    data_dict = dict(item.split("=", 1) for item in init_data.split("&") if "=" in item)
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data_dict.items()) if k != "hash")
    secret_key = sha256(bot_token.encode()).digest()
    hmac_hash = hmac.new(secret_key, check_string.encode(), sha256).hexdigest()
    return hmac_hash == data_dict.get("hash")

# -----------------------
# Middleware : vérification source
# -----------------------
@app.middleware("http")
async def check_source(request: Request, call_next):
    # Ignorer les routes publiques
    if request.url.path.startswith("/static") or request.url.path.startswith("/ping"):
        return await call_next(request)

    source = request.headers.get("X-Access-Source", "").lower()
    if source not in ALLOWED_SOURCES:
        logger.warning(f"❌ Requête bloquée - Source interdite: {source}")
        return JSONResponse(status_code=403, content={"detail": "Accès interdit : source non autorisée"})

    if source == "telegram":
        init_data = request.headers.get("X-Telegram-InitData", "")
        if not init_data or not verify_telegram_init_data(init_data):
            logger.warning("❌ Requête Telegram invalide ou initData manquant")
            return JSONResponse(status_code=403, content={"detail": "Accès interdit : Telegram initData invalide"})

    return await call_next(request)

# -----------------------
# Inclusion des routes
# -----------------------
app.include_router(auth.router, prefix="/auth", tags=["Authentification"])
app.include_router(auth_login.router, prefix="/auth", tags=["Connexion"])
app.include_router(user_profile.router, prefix="/user-data", tags=["Utilisateurs"])
app.include_router(welcome.router)
app.include_router(wallet.router)
app.include_router(balance.router)
app.include_router(friends.router)
app.include_router(mining.router, prefix="/mining", tags=["Mining"])
app.include_router(minhistory.router, prefix="/minhistory", tags=["Historique Mining"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tâches"])

# -----------------------
# Mount des fichiers statiques
# -----------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------
# Gestion des erreurs globales
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Erreur inattendue :")
    return JSONResponse(status_code=500, content={"detail": "Erreur interne du serveur", "error": str(exc)})

# -----------------------
# Startup : création des tables et pré-remplissage
# -----------------------
@app.on_event("startup")
async def startup():
    logger.info("⚡ Vérification et création des tables si nécessaire...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables créées ou déjà existantes.")

    async with AsyncSessionLocal() as session:
        await add_sample_tasks(session)
        logger.info("✅ Tâches par défaut ajoutées si elles n'existaient pas.")

# -----------------------
# Route de test
# -----------------------
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend opérationnel 🚀"}
