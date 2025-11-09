# app/main.py
import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base, AsyncSessionLocal
from app.services.addtasks import add_sample_tasks
from app.tasks.reset_daily_tasks import start_daily_reset_task  # ✅ seul import correct

from app.routes import (
    welcome, wallet, balance, user_profile,
    mining, minhistory, tasks, tradegame, bonus, actions
)
from app.routers import auth, auth_login, friends, luckygame
from app.utils import cookies

# -----------------------
# Configuration logs
# -----------------------
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("uvicorn.error")

# -----------------------
# Création de l'app
# -----------------------
app = FastAPI(
    title="BlackCoin API",
    description="Backend API pour l'application BlackCoin",
    version="1.0.0"
)

# -----------------------
# CORS
# -----------------------
frontend_origins = os.getenv("FRONTEND_URLS", "")
origins = [origin.strip() for origin in frontend_origins.split(",") if origin.strip()]

if not origins:
    logger.warning("⚠️ Aucune origine CORS définie. Fallback sur http://localhost:5173 (dev).")
    origins = ["http://localhost:5173"]

logger.info(f"🌍 CORS Origins autorisées : {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Inclusion des routes
# -----------------------
app.include_router(auth.router)
app.include_router(auth_login.router, prefix="/auth", tags=["Connexion"])
app.include_router(user_profile.router, prefix="/user-data", tags=["Utilisateurs"])
app.include_router(welcome.router)
app.include_router(wallet.router)
app.include_router(balance.router)
app.include_router(friends.router)
app.include_router(luckygame.router)
app.include_router(cookies.router)
app.include_router(tradegame.router)
app.include_router(bonus.router)
app.include_router(mining.router, prefix="/mining", tags=["Mining"])
app.include_router(minhistory.router, prefix="/minhistory", tags=["Historique Mining"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tâches"])
app.include_router(actions.router)

# -----------------------
# Fichiers statiques
# -----------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------
# Gestion globale des erreurs
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Erreur inattendue :")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur", "error": str(exc)}
    )

# -----------------------
# Startup
# -----------------------
@app.on_event("startup")
async def startup():
    logger.info("⚡ Initialisation du serveur BlackCoin...")

    # 1️⃣ Création des tables si elles n'existent pas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables vérifiées")

    # 2️⃣ Ajout des tâches par défaut
    async with AsyncSessionLocal() as session:
        await add_sample_tasks(session)
        logger.info("✅ Tâches par défaut prêtes")

    # 3️⃣ Lancement du reset automatique
    try:
        asyncio.create_task(start_daily_reset_task())  # ✅ important !
        logger.info("♻️ Tâche de reset quotidienne démarrée (5 min loop pour test).")
    except Exception as e:
        logger.error(f"❌ Impossible de lancer le reset quotidien : {e}")
