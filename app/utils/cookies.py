from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os

# ======================================================
# ⚙️ Configuration
# ======================================================
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
ENVIRONMENT = os.getenv("BACKEND_ENV", "development").lower()  # 'production' ou 'development'
IS_PROD = ENVIRONMENT == "production"

# ✅ Seules ces sources peuvent accéder à l’API
ALLOWED_SOURCES = ["telegram", "my_app"]

# ✅ Origines autorisées (CORS)
origins = [
    "https://blackcoin-v5-frontend.vercel.app",  # ton frontend vercel
    "https://t.me",  # Telegram WebApp
]

# ======================================================
# 🚀 App FastAPI
# ======================================================
app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de validation de la source
@app.middleware("http")
async def check_source(request: Request, call_next):
    source = request.headers.get("X-Access-Source")
    if source not in ALLOWED_SOURCES:
        raise HTTPException(status_code=403, detail="Accès interdit : source non autorisée")
    response = await call_next(request)
    return response

# ======================================================
# 🍪 Gestion des cookies
# ======================================================
def set_access_token_cookie(response: JSONResponse, token: str):
    """
    Définit le cookie HttpOnly pour stocker le JWT.
    - secure=True en production (HTTPS requis)
    - samesite='none' en production pour permettre le cross-site
    """
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=IS_PROD,  # True seulement en prod HTTPS
        samesite="none" if IS_PROD else "lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=expire_time,
        path="/"
    )

def clear_access_token_cookie(response: JSONResponse):
    """Supprime le cookie JWT lors du logout."""
    response.delete_cookie("access_token", path="/")

# ======================================================
# Exemple d’endpoint protégé
# ======================================================
@app.get("/secure-data")
async def secure_data():
    return {"message": "Données accessibles uniquement via Telegram ou ton app officielle ✅"}
