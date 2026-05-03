# app/routers/auth.py

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form,
    Request, Response, Cookie, status
)
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta, date
from pydantic import EmailStr
from typing import Optional

from app.models import PendingUser, User, RealCash, Wallet
from app.database import get_async_session
from app.services.VerifyEmail import generate_code, pwd_context
from app.schemas import VerificationSchema
from app.utils.token import create_access_token, create_refresh_token, verify_refresh_token
from app.services.rewards import reward_referrer
from app.services.resend_service import resend_register_code
from app.dependencies.auth import get_current_user
from app.schemas.resend import ResendCodeRequest
from app.utils.cookies import (
    set_access_token_cookie, set_refresh_token_cookie,
    refresh_tokens, clear_access_token_cookie,
)
from app.services.avatar_update import (
    generate_default_avatar, save_upload_file, make_public_url
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# ============================================================
# ✅ USER PAYLOAD
# ============================================================

def public_user_payload(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "is_verified": user.is_verified,
        "phone": getattr(user, "phone", None),
        "has_completed_welcome_tasks": user.has_completed_welcome_tasks,
        "balance": getattr(user, "balance", 0),
        "level": getattr(user, "level", 1),
        "wallet_address": getattr(user, "wallet_address", None),
    }


# ============================================================
# 🔹 REGISTER
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
    # ── 1. Validation
    if password != confirm_password:
        raise HTTPException(400, "Les mots de passe ne correspondent pas")

    existing_user = await db.execute(
        select(User).where((User.email == email) | (User.username == username))
    )
    if existing_user.scalars().first():
        raise HTTPException(409, "Utilisateur déjà existant")

    try:
        birth_date_obj = date.fromisoformat(birth_date)
    except ValueError:
        raise HTTPException(400, "Date invalide")

    # ── 2. Vérifier s'il existe déjà un pending user
    result = await db.execute(
        select(PendingUser).where(PendingUser.email == email)
    )
    existing_pending = result.scalars().first()

    # ── 3. Générer les nouvelles données
    hashed_pwd = pwd_context.hash(password)
    code = generate_code()

    now = datetime.now(timezone.utc)
    expiration = timedelta(minutes=5)

    promo_code_clean = promo_code.upper() if promo_code else None
    avatar_path = await save_upload_file(avatar) if avatar else None

    # ── 4. Si pending existe → on le remplace
    if existing_pending:
        await db.delete(existing_pending)
        await db.flush()

    # ── 5. Créer nouveau pending
    pending = PendingUser(
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date_obj,
        phone=phone,
        email=email,
        username=username,
        avatar_url=avatar_path,
        password_hash=hashed_pwd,
        verification_code=code,
        code_expires_at=now + expiration,
        created_at=now,
        promo_code_used=promo_code_clean
    )

    db.add(pending)
    await db.commit()

    return {
        "status": "verification_sent",
        "email": email,
        "verification_code": code
    }

# ============================================================
# 🔹 VERIFY EMAIL
# ============================================================

@router.post("/verify-email")
async def verify_email(
    data: VerificationSchema,
    db: AsyncSession = Depends(get_async_session)
):
    async with db.begin():

        result = await db.execute(
            select(PendingUser).where(PendingUser.email == data.email)
        )
        pending = result.scalars().first()

        if not pending:
            raise HTTPException(404, "Utilisateur non trouvé")

        if pending.verification_code != data.code:
            raise HTTPException(400, "Code incorrect")

        if datetime.now(timezone.utc) > pending.code_expires_at:
            raise HTTPException(400, "Code expiré")

        user = User(
            email=pending.email,
            first_name=pending.first_name,
            last_name=pending.last_name,
            birth_date=pending.birth_date,
            phone=pending.phone,
            username=pending.username,
            avatar_url=make_public_url(pending.avatar_url) if pending.avatar_url else None,
            password_hash=pending.password_hash,
            is_verified=True,
            has_completed_welcome_tasks=False
        )

        db.add(user)
        await db.flush()

        if not user.avatar_url:
            user.avatar_url = await generate_default_avatar(user)

        db.add(Wallet(user_id=user.id, amount=0))
        db.add(RealCash(user_id=user.id, cash_balance=0))

        # 🎁 PROMO CODE (important)
        if pending.promo_code_used:
            await reward_referrer(
                db=db,
                promo_code=pending.promo_code_used,
                new_user=user
            )

        await db.delete(pending)

    access = create_access_token({"sub": user.email})
    refresh = create_refresh_token({"sub": user.email})

    response = JSONResponse({
        "status": "success",
        "user": public_user_payload(user)
    })

    set_access_token_cookie(response, access)
    set_refresh_token_cookie(response, refresh)

    return response


@router.post("/resend-code")
async def resend_code(
    payload: ResendCodeRequest,
    db: AsyncSession = Depends(get_async_session)
):
    email = payload.email

    result = await db.execute(
        select(PendingUser).where(PendingUser.email == email)
    )
    pending = result.scalars().first()

    if not pending:
        raise HTTPException(404, "Utilisateur non trouvé")

    try:
        new_code = await resend_register_code(db, pending)
    except Exception:
        raise HTTPException(
            status_code=429,
            detail="Veuillez attendre avant de demander un nouveau code"
        )

    return {
        "status": "success",
        "verification_code": new_code,
        "expires_in": 300
    }

# ============================================================
# 🔥 COMPLETE WELCOME TASKS
# ============================================================

@router.post("/welcome/complete-tasks")
async def complete_welcome_tasks(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    if user.has_completed_welcome_tasks:
        raise HTTPException(400, "Déjà complété")

    user.has_completed_welcome_tasks = True

    # 💰 bonus
    user.balance = getattr(user, "balance", 0) + 4950

    result = await db.execute(
        select(RealCash).where(RealCash.user_id == user.id)
    )
    cash = result.scalars().first()
    if cash:
        cash.cash_balance += 50

    await db.commit()

    return {"user": public_user_payload(user)}


# ============================================================
# 🔹 ME
# ============================================================

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    return {"status": "success", "user": public_user_payload(user)}


# ============================================================
# 🔹 LOGOUT
# ============================================================

@router.post("/logout")
async def logout():
    response = JSONResponse({"status": "success"})
    clear_access_token_cookie(response)
    response.delete_cookie("refresh_token", path="/")
    return response


# ============================================================
# 🔹 REFRESH
# ============================================================

@router.post("/refresh")
async def refresh_token_endpoint(
    response: Response,
    refresh_token: str = Cookie(None),
    db: AsyncSession = Depends(get_async_session)
):
    if not refresh_token:
        raise HTTPException(401, "Refresh token manquant")

    payload = verify_refresh_token(refresh_token)
    email = payload.get("sub")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()

    if not user:
        raise HTTPException(401, "Utilisateur non trouvé")

    return refresh_tokens(response, email)