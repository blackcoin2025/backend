# app/utils/handler.py
from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
from app.utils.token import create_access_token, create_refresh_token

ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7


def set_access_token_cookie(response: JSONResponse, token: str, is_prod: bool = False):
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax" if not is_prod else "none",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=expire_time,
        path="/"
    )


def set_refresh_token_cookie(response: JSONResponse, token: str, is_prod: bool = False):
    expire_time = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=is_prod,
        samesite="lax" if not is_prod else "none",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=expire_time,
        path="/"
    )


def clear_access_token_cookie(response: JSONResponse):
    """Supprime uniquement l'access_token (ex: expiration courte)."""
    response.delete_cookie("access_token", path="/")


def clear_auth_cookies(response: JSONResponse):
    """Supprime access_token + refresh_token (ex: logout complet)."""
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


def refresh_tokens(response: JSONResponse, user_email: str, is_prod: bool = False):
    """
    Génère un nouvel access_token et refresh_token pour un utilisateur,
    puis met à jour les cookies.
    """
    access_token = create_access_token({"sub": user_email})
    refresh_token = create_refresh_token({"sub": user_email})

    set_access_token_cookie(response, access_token, is_prod)
    set_refresh_token_cookie(response, refresh_token, is_prod)

    return {"access_token": access_token, "refresh_token": refresh_token}
