from datetime import datetime, timedelta, timezone
from typing import Union
from fastapi import APIRouter, Response, Cookie, HTTPException
from fastapi.responses import JSONResponse
from app.utils.token import create_access_token, create_refresh_token, verify_refresh_token
import os

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 15))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))
ENV = os.getenv("BACKEND_ENV", "production")
IS_PROD = ENV == "production"

router = APIRouter()


def _to_unix_timestamp(dt: datetime) -> int:
    return int(dt.astimezone(timezone.utc).timestamp())

def _samesite_value() -> str:
    return "None" if IS_PROD else "Lax"


def set_access_token_cookie(response: Union[Response, JSONResponse], token: str):
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=IS_PROD,
        samesite=_samesite_value(),
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=_to_unix_timestamp(expire_time),
        path="/",
    )

def set_refresh_token_cookie(response: Union[Response, JSONResponse], token: str):
    expire_time = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    response.set_cookie(
        key="refresh_token",
        value=token,
        httponly=True,
        secure=IS_PROD,
        samesite=_samesite_value(),
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        expires=_to_unix_timestamp(expire_time),
        path="/",
    )

def refresh_tokens(response: Union[Response, JSONResponse], user_email: str) -> dict:
    access_token = create_access_token(data={"sub": user_email})
    refresh_token = create_refresh_token(data={"sub": user_email})
    set_access_token_cookie(response, access_token)
    set_refresh_token_cookie(response, refresh_token)
    return {"access_token": access_token, "refresh_token": refresh_token}


def clear_access_token_cookie(response: Union[Response, JSONResponse]) -> None:
    response.delete_cookie("access_token", path="/")

def clear_auth_cookies(response: Union[Response, JSONResponse]) -> None:
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")


@router.post("/auth/refresh")
def refresh_token_endpoint(
    response: Response,
    refresh_token: str = Cookie(None),
):
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token manquant")

    try:
        payload = verify_refresh_token(refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Refresh token invalide ou expiré")

    user_email = payload.get("sub")
    if not user_email:
        raise HTTPException(status_code=401, detail="Refresh token invalide")

    return refresh_tokens(response, user_email)
