from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from jose import jwt, JWTError
import os
from fastapi import HTTPException, status

# -------------------------------
# Variables d'environnement (injectées par Render)
# -------------------------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY est manquant dans les variables d'environnement")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

# -------------------------------
# Création d'un JWT
# -------------------------------
def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Crée un token JWT signé avec une durée de validité.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# -------------------------------
# Décodage simple (retourne None si invalide)
# -------------------------------
def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Décode un JWT.
    Retourne le payload si valide, None sinon.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# -------------------------------
# Vérification stricte avec FastAPI
# -------------------------------
def verify_access_token(token: str) -> Dict[str, Any]:
    """
    Vérifie un JWT et renvoie le payload si valide.
    Lève une HTTPException si invalide ou expiré.
    """
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
        )
    return payload
