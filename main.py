from dotenv import load_dotenv
load_dotenv()

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import engine, Base
from app.services.addtasks import add_sample_tasks
from app.database import AsyncSessionLocal
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
    "https://blackcoin-v5-frontend.vercel.app"
]

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
    return JSONResponse(
        status_code=500,
        content={"detail": "Erreur interne du serveur", "error": str(exc)}
    )

# -----------------------
# Startup : création des tables et pré-remplissage
# -----------------------
@app.on_event("startup")
async def startup():
    logger.info("⚡ Vérification et création des tables si nécessaire...")
    async with engine.begin() as conn:
        # Crée toutes les tables définies dans Base si elles n'existent pas
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Tables créées ou déjà existantes.")

    # Pré-remplir les tâches si nécessaire
    async with AsyncSessionLocal() as session:
        await add_sample_tasks(session)
        logger.info("✅ Tâches par défaut ajoutées si elles n'existaient pas.")

# -----------------------
# Route de test
# -----------------------
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend opérationnel 🚀"}
