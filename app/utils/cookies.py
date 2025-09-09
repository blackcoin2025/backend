from datetime import datetime, timedelta, timezone
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import hmac, hashlib
from urllib.parse import parse_qsl

# ======================================================
# ⚙️ Configuration
# ======================================================
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))
ENVIRONMENT = os.getenv("BACKEND_ENV", "development").lower()  # 'production' ou 'development'
IS_PROD = ENVIRONMENT == "production"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # obligatoire pour vérifier initData

# Origines autorisées (CORS)
origins = [
    "https://blackcoin-v5-frontend.vercel.app",
    "https://t.me",  # Telegram WebApp
]

# ======================================================
# 🚀 App FastAPI
# ======================================================
app = FastAPI(title="BlackCoin API", version="1.0.0")

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 🍪 Gestion des cookies
# ======================================================
def set_access_token_cookie(response: JSONResponse, token: str):
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=IS_PROD,
        samesite="none" if IS_PROD else "lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=expire_time,
        path="/"
    )

def clear_access_token_cookie(response: JSONResponse):
    response.delete_cookie("access_token", path="/")

# ======================================================
# 🔐 Vérification Telegram initData
# ======================================================
def verify_telegram_init_data(init_data: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not init_data:
        return False

    try:
        data = dict(parse_qsl(init_data))
        hash_received = data.pop("hash", None)
        if not hash_received:
            return False

        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
        secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode()).digest()
        hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        return hmac_hash == hash_received
    except Exception:
        return False

# ======================================================
# Middleware : bloquer tout accès hors Telegram
# ======================================================
@app.middleware("http")
async def check_telegram_source(request: Request, call_next):
    # Skip /ping endpoint or static files for debug
    if request.url.path.startswith("/ping") or request.url.path.startswith("/static"):
        return await call_next(request)

    init_data = request.headers.get("X-Telegram-InitData", "")
    if not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Accès interdit : non Telegram")

    response = await call_next(request)
    return response

# ======================================================
# Exemple d’endpoint protégé
# ======================================================
@app.get("/secure-data")
async def secure_data():
    return {"message": "Données accessibles uniquement via Telegram ou ton app officielle ✅"}

# ======================================================
# Route de test publique
# ======================================================
@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "Backend opérationnel 🚀"}
