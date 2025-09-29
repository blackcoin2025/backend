import os
import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base, AsyncSessionLocal
from app.services.addtasks import add_sample_tasks
from app.routes import welcome, wallet, balance, user_profile, mining, minhistory, tasks, tradegame
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

# Fallback dev
if not origins:
    logger.warning("⚠️ Aucune origine CORS définie. Fallback sur http://localhost:5173 (dev).")
    origins = ["http://localhost:5173"]

logger.info(f"🌍 CORS Origins autorisées : {origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,   # nécessaire pour les cookies JWT
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Inclusion routes
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
app.include_router(mining.router, prefix="/mining", tags=["Mining"])
app.include_router(minhistory.router, prefix="/minhistory", tags=["Historique Mining"])
app.include_router(tasks.router, prefix="/tasks", tags=["Tâches"])

# -----------------------
# Fichiers statiques
# -----------------------
app.mount("/static", StaticFiles(directory="static"), name="static")

# -----------------------
# Gestion globale erreurs
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
    logger.info("⚡ Vérification des tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables OK")

    async with AsyncSessionLocal() as session:
        await add_sample_tasks(session)
        logger.info("✅ Tâches par défaut prêtes")

# -----------------------
# Route test
# -----------------------
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend opérationnel 🚀"}
