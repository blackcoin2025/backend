from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_async_session
from app.models import User
from app.schemas import LoginRequest
from app.services.VerifyEmail import pwd_context
from app.utils.token import create_access_token, create_refresh_token
from app.utils.cookies import set_access_token_cookie, set_refresh_token_cookie

router = APIRouter()


# ============================================================
# 🔹 USER PAYLOAD
# ============================================================
def public_user_payload(user: User):
    return {
        "id": int(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "username": user.username,
        "phone": user.phone,
        "is_verified": bool(user.is_verified),
        "has_completed_welcome_tasks": bool(user.has_completed_welcome_tasks),
        "requires_onboarding": not user.has_completed_welcome_tasks,  # 🔥 IMPORTANT
        "balance": getattr(user, "balance", 0),
        "level": getattr(user, "level", 1),
        "wallet_address": getattr(user, "wallet_address", None),
    }


# ============================================================
# 🔹 LOGIN
# ============================================================
@router.post("/login")
async def login_user(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    # ── 1) Validation
    email = (payload.email or "").strip() or None
    username = (payload.username or "").strip() or None
    password = payload.password

    if not password:
        raise HTTPException(400, "Mot de passe requis")

    if not email and not username:
        raise HTTPException(400, "Email ou username requis")

    # ── 2) Recherche user
    if email and username:
        query = select(User).where(
            or_(User.email == email, User.username == username)
        )
    elif email:
        query = select(User).where(User.email == email)
    else:
        query = select(User).where(User.username == username)

    result = await db.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(401, "Identifiants invalides")

    if email and username and (user.email != email or user.username != username):
        raise HTTPException(401, "Identifiants invalides")

    # ── 3) Password
    if not pwd_context.verify(password, user.password_hash):
        raise HTTPException(401, "Identifiants invalides")

    # ── 4) Vérification email
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Veuillez vérifier votre email."
        )

    # ── 5) Tokens
    access_token = create_access_token({"sub": user.email})
    refresh_token = create_refresh_token({"sub": user.email})

    # ── 6) Réponse enrichie
    response = JSONResponse({
        "status": "success",
        "user": public_user_payload(user)
    })

    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)

    return response