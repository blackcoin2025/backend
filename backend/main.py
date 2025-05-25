from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.database import get_db, engine
from backend import models, schemas
from backend.models import User, Profile, Wallet, EmailVerificationCode
from backend.telegram_bot import verify_telegram_username
from backend.routes.user_data import router as user_router
from backend.auth import get_password_hash
from backend.email_service import send_verification_email
from backend.routes.admin_routes import router as admin_router
app.include_router(admin_router, tags=["Admin"])

import os
import random
import requests
from dotenv import load_dotenv


# ---------------------- Initialisation de l'application FastAPI ----------------------
app = FastAPI()
load_dotenv()

# ✅ Ajoute ton frontend ici
origins = [
    "https://blackcoin-v5-frontend.vercel.app",
    "http://localhost:3000",  # pour le dev local éventuellement
]

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_TELEGRAM = os.getenv("ADMIN_TELEGRAM")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 🔥 Ne mets pas ["*"] si tu envoies des cookies ou headers protégés
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------- Création des tables + configuration du webhook Telegram ----------------------

@app.on_event("startup")
async def startup():
    # Création des tables
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    # Configuration du webhook Telegram
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")  # Exemple : https://blackcoin-backend.onrender.com/webhook

    if telegram_token and webhook_url:
        telegram_api_url = f"https://api.telegram.org/bot{telegram_token}/setWebhook"
        response = requests.post(telegram_api_url, data={"url": webhook_url})
        print("✅ Webhook Telegram défini :", response.json())
    else:
        print("❌ TELEGRAM_BOT_TOKEN ou WEBHOOK_URL manquant dans les variables d’environnement.")

# ---------------------- ROUTE 1 : Inscription + envoi du code de vérification ----------------------

@app.post("/register", response_model=schemas.Message)
async def register_user(user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas.")

    result = await db.execute(
        select(User).filter(
            (User.email == user_data.email) | (User.telegram_username == user_data.telegram_username)
        )
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email ou nom d'utilisateur Telegram déjà utilisé.")

    hashed_password = get_password_hash(user_data.password)

    new_user = User(
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        birth_date=user_data.birth_date,
        phone=user_data.phone,
        email=user_data.email,
        telegram_username=user_data.telegram_username,
        password_hash=hashed_password,
        is_verified=False
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    code = str(random.randint(100000, 999999))
    email_code = EmailVerificationCode(user_id=new_user.id, code=code)
    db.add(email_code)
    await db.commit()

    send_verification_email(user_data.email, code)

    return {"detail": "Code de vérification envoyé à votre adresse email."}

# ---------------------- ROUTE 2 : Vérification de l'email ----------------------

@app.post("/verify-email", response_model=schemas.Message)
async def verify_email(data: schemas.EmailCodeIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")

    result = await db.execute(select(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id))
    code_entry = result.scalars().first()
    if not code_entry or code_entry.code != data.code:
        raise HTTPException(status_code=400, detail="Code de vérification incorrect.")

    telegram_info = await verify_telegram_username(user.telegram_username)
    if not telegram_info:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur Telegram invalide.")

    user.telegram_id = telegram_info["id"]
    user.telegram_photo = telegram_info.get("photo_url")
    user.is_verified = True
    await db.commit()

    profile = Profile(user_id=user.id)
    wallet = Wallet(user_id=user.id)
    db.add_all([profile, wallet])
    await db.commit()

    return {"detail": "Votre compte a été vérifié et créé avec succès."}

# ---------------------- ROUTE 3 : Webhook Telegram ----------------------

@app.post("/webhook")
async def telegram_webhook(request: Request):
    payload = await request.json()
    print("📩 Nouveau message Telegram reçu :", payload)
    return {"ok": True}

# ---------------------- ROUTES UTILISATEUR ----------------------

app.include_router(user_router, tags=["Utilisateur"])
app.include_router(admin_router, tags=["Admin"])

# ---------------------- ROUTE DE TEST ROOT ----------------------

@app.get("/")
def read_root():
    return {"message": "🚀 Backend BlackCoin en ligne !"}
