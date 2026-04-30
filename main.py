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

# 🔥 RESET TASK
from app.tasks.reset_daily_tasks import start_daily_reset_task

from app.routes import (
    welcome, wallet, balance, user_profile, eligibility,
    mining, minhistory, tasks, tradegame, bonus, actions, cashmoney
)
from app.routers import auth, auth_login, friends, luckygame
from app.utils import cookies
from app.routes import myassets
from app.routes import dailytasks


# -----------------------
# ENV
# -----------------------
ENV = os.getenv("ENV", "dev")  # dev | prod | test


# -----------------------
# LOGS
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# -----------------------
# APP
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
origins = [o.strip() for o in frontend_origins.split(",") if o.strip()]

if ENV == "dev":
    if not origins:
        logger.warning("⚠️ DEV: fallback sur localhost")
        origins = ["http://localhost:5173"]
else:
    if not origins:
        raise ValueError("❌ FRONTEND_URLS requis en production")

logger.info(f"🌍 CORS autorisées : {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------
# ROUTES
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
app.include_router(cashmoney.router)
app.include_router(mining.router, prefix="/mining", tags=["Mining"])
app.include_router(minhistory.router, prefix="/minhistory", tags=["Historique Mining"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tâches"])
app.include_router(actions.router)
app.include_router(eligibility.router)
app.include_router(myassets.router)
app.include_router(dailytasks.router)


# -----------------------
# STATIC
# -----------------------
app.mount("/static", StaticFiles(directory="static"), name="static")


# -----------------------
# ERREURS GLOBALES
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("❌ Erreur serveur")
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur"}
    )


# -----------------------
# STARTUP
# -----------------------
@app.on_event("startup")
async def startup():
    logger.info(f"⚡ Démarrage BlackCoin API [{ENV}]")

    # -----------------------
    # DEV INIT DB
    # -----------------------
    if ENV == "dev":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Tables créées (dev)")

        async with AsyncSessionLocal() as session:
            await add_sample_tasks(session)
        logger.info("✅ Sample tasks ajoutées (dev)")

    # -----------------------
    # RESET TASK (SAFE)
    # -----------------------
    if ENV != "test":
        try:
            asyncio.create_task(start_daily_reset_task())
            logger.info("♻️ Reset task scheduler lancé")
        except Exception as e:
            logger.error(f"❌ Reset scheduler error: {e}")