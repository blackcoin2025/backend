from fastapi import FastAPI, HTTPException, Depends
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

import random

# ---------------------- Initialisation de l'application FastAPI ----------------------

app = FastAPI()

# ---------------------- Middleware CORS ----------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # À restreindre à ton domaine frontend en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------- Création automatique des tables à la startup ----------------------

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

# ---------------------- ROUTE 1 : Inscription + envoi du code de vérification ----------------------

@app.post("/register", response_model=schemas.Message)
async def register_user(user_data: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    if user_data.password != user_data.confirm_password:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas.")

    # Vérifie si un utilisateur existe déjà avec le même email ou nom d'utilisateur Telegram
    result = await db.execute(
        select(User).filter(
            (User.email == user_data.email) | (User.telegram_username == user_data.telegram_username)
        )
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email ou nom d'utilisateur Telegram déjà utilisé.")

    # Hasher le mot de passe
    hashed_password = get_password_hash(user_data.password)

    # Création du nouvel utilisateur (sans Telegram ID)
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

    # Générer un code de vérification aléatoire à 6 chiffres
    code = str(random.randint(100000, 999999))
    email_code = EmailVerificationCode(user_id=new_user.id, code=code)
    db.add(email_code)
    await db.commit()

    # Envoi du code de vérification par email
    send_verification_email(user_data.email, code)

    return {"detail": "Code de vérification envoyé à votre adresse email."}

# ---------------------- ROUTE 2 : Vérification de l'email ----------------------

@app.post("/verify-email", response_model=schemas.Message)
async def verify_email(data: schemas.EmailCodeIn, db: AsyncSession = Depends(get_db)):
    # Récupération de l'utilisateur par email
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé.")

    # Récupération du code de vérification associé à l'utilisateur
    result = await db.execute(select(EmailVerificationCode).where(EmailVerificationCode.user_id == user.id))
    code_entry = result.scalars().first()
    if not code_entry or code_entry.code != data.code:
        raise HTTPException(status_code=400, detail="Code de vérification incorrect.")

    # Vérification du nom d'utilisateur Telegram via l'API
    telegram_info = await verify_telegram_username(user.telegram_username)
    if not telegram_info:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur Telegram invalide.")

    # Mise à jour des informations de l'utilisateur
    user.telegram_id = telegram_info["id"]
    user.telegram_photo = telegram_info.get("photo_url")
    user.is_verified = True
    await db.commit()

    # Création du profil utilisateur et du wallet
    profile = Profile(user_id=user.id)
    wallet = Wallet(user_id=user.id)
    db.add_all([profile, wallet])
    await db.commit()

    return {"detail": "Votre compte a été vérifié et créé avec succès."}

# ---------------------- ROUTES UTILISATEUR ----------------------

app.include_router(user_router, tags=["Utilisateur"])
