from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
import os

# ✅ Charger les variables d'environnement si nécessaire
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
ENVIRONMENT = os.getenv("BACKEND_ENV", "development").lower()  # 'production' ou 'development'

IS_PROD = ENVIRONMENT == "production"

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
