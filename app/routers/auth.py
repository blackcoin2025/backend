# app/routers/auth.py
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request, Response, Cookie
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
from app.services.VerifyEmail import generate_code, send_verification_email, pwd_context
from app.schemas import VerificationSchema
from app.utils.token import create_access_token, create_refresh_token, verify_refresh_token
from app.utils.auth_utils import get_user_by_email
from app.services.rewards import reward_referrer
from app.dependencies.auth import get_current_user
from app.utils.cookies import (
    set_access_token_cookie,
    set_refresh_token_cookie,
    refresh_tokens,
    clear_access_token_cookie,
    clear_auth_cookies,
)

router = APIRouter(prefix="/auth", tags=["Auth"])

ACCESS_TOKEN_EXPIRE_MINUTES = 15

# ============================================================
# ✅ Utils locaux
# ============================================================

def ensure_static_uploads_dir() -> str:
    base = os.path.join("static", "uploads")
    os.makedirs(base, exist_ok=True)
    return base

def public_user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "avatar_url": user.avatar_url,
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

    # Vérifier doublon email/username
    dup_user = await db.execute(
        select(User).where((User.email == email) | (User.username == username))
    )
    if dup_user.scalars().first():
        raise HTTPException(status_code=409, detail="E-mail ou nom d'utilisateur déjà utilisé.")

    # Upload avatar sécurisé
    avatar_url = None
    if avatar:
        if avatar.content_type not in ["image/jpeg", "image/png"]:
            raise HTTPException(status_code=400, detail="Format d'image non supporté")
        uploads_dir = ensure_static_uploads_dir()
        filename = f"{uuid4().hex}_{os.path.basename(avatar.filename)}"
        path = os.path.join(uploads_dir, filename)
        content = await avatar.read()
        with open(path, "wb") as f:
            f.write(content)
        avatar_url = f"/static/uploads/{filename}"

    try:
        birth_date_obj = date.fromisoformat(birth_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide. Format attendu : YYYY-MM-DD.")

    hashed_pwd = pwd_context.hash(password)
    code = generate_code()
    now = datetime.utcnow()

    existing_pending = await db.execute(select(PendingUser).where(PendingUser.email == email))
    pending = existing_pending.scalars().first()
    promo_code_clean = promo_code.upper() if promo_code else None

    if pending:
        pending.first_name = first_name
        pending.last_name = last_name
        pending.birth_date = birth_date_obj
        pending.phone = phone
        pending.username = username
        pending.avatar_url = avatar_url
        pending.password_hash = hashed_pwd
        pending.verification_code = code
        pending.code_expires_at = now + timedelta(minutes=15)
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
            avatar_url=avatar_url,
            password_hash=hashed_pwd,
            verification_code=code,
            code_expires_at=now + timedelta(minutes=15),
            is_verified=False,
            created_at=now,
            promo_code_used=promo_code_clean
        )
        db.add(pending)

    await db.commit()

    try:
        send_verification_email(email, code)
    except Exception:
        pass

    return {
    "status": "verification_sent",
    "next": "verify_email",
    "email": email,
    "detail": "Un code de vérification a été envoyé à votre adresse e-mail."
}

# ============================================================
# 🔹 Verify Email
# ============================================================

@router.post("/verify-email")
async def verify_email(
    data: VerificationSchema,
    db: AsyncSession = Depends(get_async_session)
):
    # Vérification utilisateur existant
    existing_user = await get_user_by_email(db, data.email)
    if existing_user:
        access_token = create_access_token({"sub": existing_user.email})
        refresh_token = create_refresh_token({"sub": existing_user.email})

        response = JSONResponse(
            {"status": "success", "user": public_user_payload(existing_user)}
        )
        set_access_token_cookie(response, access_token)
        set_refresh_token_cookie(response, refresh_token)
        return response

    # Vérifier utilisateur en attente
    result = await db.execute(
        select(PendingUser).where(PendingUser.email == data.email)
    )
    pending = result.scalars().first()
    if not pending:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")
    if pending.verification_code != data.code:
        raise HTTPException(status_code=400, detail="Code incorrect")
    if datetime.utcnow() > pending.code_expires_at:
        raise HTTPException(status_code=400, detail="Code expiré")

    user = User(
        email=pending.email,
        first_name=pending.first_name,
        last_name=pending.last_name,
        birth_date=pending.birth_date,
        phone=pending.phone,
        username=pending.username,
        avatar_url=pending.avatar_url,
        password_hash=pending.password_hash,
        is_verified=True,
        has_completed_welcome_tasks=False
    )
    db.add(user)

    # Récompense si promo code utilisé
    if pending.promo_code_used:
        try:
            await reward_referrer(db, promo_code=pending.promo_code_used, new_user=user)
        except Exception as e:
            print(f"Erreur reward_referrer: {e}")

        promo_q = select(PromoCode).where(PromoCode.code == pending.promo_code_used)
        promo = (await db.execute(promo_q)).scalar_one_or_none()
        if promo:
            db.add(Friend(user_id=promo.user_id, friend_id=user.id, status="accepted"))

    await db.delete(pending)
    await db.commit()

    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    response = JSONResponse({"status": "success", "user": public_user_payload(user)})
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    return response

# ============================================================
# 🔹 Get Current User (/auth/me)
# ============================================================

@router.get("/me")
async def get_me(request: Request, current_user: User = Depends(get_current_user)):
    print("🚀 Headers reçus :", request.headers)
    access_token = request.cookies.get("access_token")
    print("🚀 Cookie access_token reçu :", access_token)
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

    # Vérifier que l’utilisateur existe
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")

    return refresh_tokens(response, email)
