from datetime import datetime, timedelta, timezone
from fastapi.responses import JSONResponse
import os

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

def set_access_token_cookie(response: JSONResponse, token: str, is_prod: bool = False):
    """
    Définit le cookie HttpOnly pour stocker le JWT.
    """
    expire_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=is_prod,                 # True en prod HTTPS
        samesite="lax" if not is_prod else "none",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=expire_time,            # datetime UTC ✅
        path="/"
    )

def clear_access_token_cookie(response: JSONResponse):
    """Supprime le cookie JWT lors du logout."""
    response.delete_cookie("access_token", path="/")
