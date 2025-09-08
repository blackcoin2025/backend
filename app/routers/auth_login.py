# app/routes/auth_login.py

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from app.database import get_async_session
from app.models import User
from app.schemas import LoginRequest
from app.services.VerifyEmail import pwd_context
from app.utils.token import create_access_token
from app.utils.cookies import set_access_token_cookie  # ⚡ fonction utilitaire cookies

router = APIRouter()


@router.post("/login")
async def login_user(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Authentifie un utilisateur par email OU username + mot de passe.
    Stocke le JWT dans un cookie HttpOnly sécurisé.
    Retourne uniquement les infos utilisateur (pas le token).
    """

    # ── 1) Validation des champs d'entrée
    email = (payload.email or "").strip() or None
    username = (payload.username or "").strip() or None
    password = payload.password

    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le mot de passe est requis."
        )

    if not email and not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fournissez au moins l'email ou le nom d'utilisateur."
        )

    # ── 2) Récupération de l'utilisateur (email OU username)
    if email and username:
        query = select(User).where(or_(User.email == email, User.username == username))
    elif email:
        query = select(User).where(User.email == email)
    else:
        query = select(User).where(User.username == username)

    result = await db.execute(query)
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides."
        )

    # Vérifie cohérence email + username si les deux sont fournis
    if email and username:
        if (user.email != email) or (user.username != username):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Identifiants invalides."
            )

    # ── 3) Vérification mot de passe
    if not pwd_context.verify(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides."
        )

    # ── 4) Création du token JWT
    token = create_access_token(data={"sub": user.email})

    # ── 5) Réponse avec cookie (pas de token dans le JSON)
    user_data = {
        "id": int(user.id),
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "username": user.username,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "is_verified": bool(user.is_verified),
        "has_completed_welcome_tasks": bool(user.has_completed_welcome_tasks),
    }

    response = JSONResponse(content={
        "user": user_data,
        "message": "Connexion réussie."
    })

    # ⚡ Ajoute le cookie sécurisé
    set_access_token_cookie(response, token)

    return response
