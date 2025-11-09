# app/routers/auth.py
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form,
    Request, Response, Cookie
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timedelta, date
from pydantic import EmailStr
from uuid import uuid4
import os
from typing import Optional

from app.models import PendingUser, User, PromoCode, Friend
from app.database import get_async_session
from app.services.VerifyEmail import generate_code, pwd_context
from app.schemas import VerificationSchema
from app.utils.token import create_access_token, create_refresh_token, verify_refresh_token
from app.utils.auth_utils import get_user_by_email
from app.services.rewards import reward_referrer
from app.dependencies.auth import get_current_user
from app.utils.cookies import (
    set_access_token_cookie, set_refresh_token_cookie,
    refresh_tokens, clear_access_token_cookie,
)
# Utilitaires avatar : centralise la sauvegarde et la conversion d'URL
from app.services.avatar_update import (
    generate_default_avatar, save_upload_file, make_public_url
)

router = APIRouter(prefix="/auth", tags=["Auth"])

ACCESS_TOKEN_EXPIRE_MINUTES = 15

# ============================================================
# ✅ Utils
# ============================================================

def public_user_payload(user: User) -> dict:
    """Construit la charge utile publique d’un utilisateur."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": make_public_url(user.avatar_url) if getattr(user, "avatar_url", None) else None,
        "is_verified": user.is_verified,
        "phone": getattr(user, "phone", None),
        "has_completed_welcome_tasks": user.has_completed_welcome_tasks,
        "balance": getattr(user, "balance", 0),
        "level": getattr(user, "level", 1),
        "wallet_address": getattr(user, "wallet_address", None),
    }

# ============================================================
# 🔹 Register
# ============================================================
@router.post("/register", status_code=201)
async def register_user(
    first_name: str = Form(...),
    last_name: str = Form(...),
    birth_date: str = Form(...),
    phone: str = Form(...),
    email: EmailStr = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    promo_code: Optional[str] = Form(None),
    avatar: UploadFile = File(None),
    db: AsyncSession = Depends(get_async_session)
):
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Les mots de passe ne correspondent pas.")

    # Vérification doublons
    dup_user = await db.execute(
        select(User).where((User.email == email) | (User.username == username))
    )
    if dup_user.scalars().first():
        raise HTTPException(status_code=409, detail="E-mail ou nom d'utilisateur déjà utilisé.")

    # Traitement date
    try:
        birth_date_obj = date.fromisoformat(birth_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide. Format attendu : YYYY-MM-DD.")

    hashed_pwd = pwd_context.hash(password)
    code = generate_code()
    now = datetime.utcnow()
    expiration = timedelta(minutes=5)
    promo_code_clean = promo_code.upper() if promo_code else None

    # --- Gestion de l'avatar
    avatar_rel_path = None
    if avatar:
        avatar_rel_path = await save_upload_file(avatar)

    # Crée ou met à jour PendingUser
    existing_pending = await db.execute(select(PendingUser).where(PendingUser.email == email))
    pending = existing_pending.scalars().first()

    if pending:
        pending.first_name = first_name
        pending.last_name = last_name
        pending.birth_date = birth_date_obj
        pending.phone = phone
        pending.username = username
        if avatar_rel_path:
            pending.avatar_url = avatar_rel_path
        pending.password_hash = hashed_pwd
        pending.verification_code = code
        pending.code_expires_at = now + expiration
        pending.created_at = now
        pending.promo_code_used = promo_code_clean
    else:
        pending = PendingUser(
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date_obj,
            phone=phone,
            email=email,
            username=username,
            avatar_url=avatar_rel_path,
            password_hash=hashed_pwd,
            verification_code=code,
            code_expires_at=now + expiration,
            is_verified=False,
            created_at=now,
            promo_code_used=promo_code_clean
        )
        db.add(pending)

    await db.commit()

    return JSONResponse(
        content={
            "status": "verification_sent",
            "next": "verify_email",
            "email": email,
            "verification_code": code,
            "expires_in": int(expiration.total_seconds()),
            "detail": "Code de vérification généré (affiché côté frontend)."
        },
        status_code=201
    )

# ============================================================
# 🔹 Verify Email
# ============================================================
@router.post("/verify-email")
async def verify_email(
    data: VerificationSchema,
    db: AsyncSession = Depends(get_async_session)
):
    pending_result = await db.execute(select(PendingUser).where(PendingUser.email == data.email))
    pending = pending_result.scalars().first()
    if not pending:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    if pending.verification_code != data.code:
        raise HTTPException(status_code=400, detail="Code incorrect")
    if datetime.utcnow() > pending.code_expires_at:
        raise HTTPException(status_code=400, detail="Code expiré")

    # --- Avatar final
    # Si PendingUser avait fourni un fichier -> convertit en URL publique
    avatar_final = make_public_url(pending.avatar_url) if pending.avatar_url else None

    user = User(
        email=pending.email,
        first_name=pending.first_name,
        last_name=pending.last_name,
        birth_date=pending.birth_date,
        phone=pending.phone,
        username=pending.username,
        avatar_url=avatar_final,
        password_hash=pending.password_hash,
        is_verified=True,
        has_completed_welcome_tasks=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Si pas d’avatar fourni, générer un avatar par défaut basé sur le User.id
    if not pending.avatar_url:
        avatar_final = await generate_default_avatar(user)
        user.avatar_url = avatar_final
        await db.commit()

    # Gestion parrainage
    if pending.promo_code_used:
        try:
            await reward_referrer(db, promo_code=pending.promo_code_used, new_user=user)
        except Exception as e:
            print(f"Erreur reward_referrer: {e}")
        promo_q = select(PromoCode).where(PromoCode.code == pending.promo_code_used)
        promo = (await db.execute(promo_q)).scalar_one_or_none()
        if promo:
            db.add(Friend(user_id=promo.user_id, friend_id=user.id, status="accepted"))

    # Supprime PendingUser
    await db.delete(pending)
    await db.commit()

    # Tokens et réponse
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})
    response = JSONResponse({"status": "success", "user": public_user_payload(user)})
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    return response

    # Récupère pending user
    result = await db.execute(select(PendingUser).where(PendingUser.email == data.email))
    pending = result.scalars().first()
    if not pending:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    if pending.verification_code != data.code:
        raise HTTPException(status_code=400, detail="Code incorrect")
    if datetime.utcnow() > pending.code_expires_at:
        raise HTTPException(status_code=400, detail="Code expiré")

    # Prépare avatar_final : convertit le chemin relatif stocké en URL publique
    avatar_final = make_public_url(pending.avatar_url) if pending.avatar_url else None

    # Crée l'utilisateur final en utilisant avatar_final (peut être None)
    user = User(
        email=pending.email,
        first_name=pending.first_name,
        last_name=pending.last_name,
        birth_date=pending.birth_date,
        phone=pending.phone,
        username=pending.username,
        avatar_url=avatar_final,
        password_hash=pending.password_hash,
        is_verified=True,
        has_completed_welcome_tasks=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Si aucun avatar fourni à l'inscription -> génère un avatar par défaut (ne remplace pas si déjà présent)
    if not pending.avatar_url:
        avatar_final = await generate_default_avatar(user)
        user.avatar_url = avatar_final
        await db.commit()

    # Gestion du parrainage (si promo_code_used)
    if pending.promo_code_used:
        try:
            await reward_referrer(db, promo_code=pending.promo_code_used, new_user=user)
        except Exception as e:
            print(f"Erreur reward_referrer: {e}")

        promo_q = select(PromoCode).where(PromoCode.code == pending.promo_code_used)
        promo = (await db.execute(promo_q)).scalar_one_or_none()
        if promo:
            db.add(Friend(user_id=promo.user_id, friend_id=user.id, status="accepted"))

    # Supprime l'enregistrement pending
    await db.delete(pending)
    await db.commit()

    # Génération tokens et réponse
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    response = JSONResponse({"status": "success", "user": public_user_payload(user)})
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    return response

# ============================================================
# 🔹 Get Current User
# ============================================================

@router.get("/me")
async def get_me(request: Request, current_user: User = Depends(get_current_user)):
    return {"status": "success", "user": public_user_payload(current_user)}

# ============================================================
# 🔹 Logout
# ============================================================

@router.post("/logout")
async def logout():
    response = JSONResponse({"status": "success", "detail": "Déconnecté"})
    clear_access_token_cookie(response)
    response.delete_cookie("refresh_token", path="/")
    return response

# ============================================================
# 🔹 Refresh Token
# ============================================================

@router.post("/refresh")
async def refresh_token_endpoint(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_async_session)
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token manquant")

    payload = verify_refresh_token(refresh_token)
    email = payload.get("sub")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    return refresh_tokens(response, email)
