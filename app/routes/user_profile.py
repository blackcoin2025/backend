from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from datetime import date
import os
import shutil
from uuid import uuid4

from app.database import get_async_session
from app.dependencies.auth import get_current_user
from app.dependencies.dependency import require_completed_welcome
from app.models import User
from app.schemas import UserOut

# 🔥 CONFIG
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
UPLOAD_DIR = "static/avatars"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_FILE_SIZE_MB = 5

router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================
# 🔹 PROFIL UTILISATEUR CONNECTÉ (PROTÉGÉ)
# ============================================================
@router.get("/me", response_model=UserOut)
async def get_my_profile(
    current_user: User = Depends(require_completed_welcome)
):
    return current_user


# ============================================================
# 🔹 PROFIL PUBLIC (NON PROTÉGÉ)
# ============================================================
@router.get("/{user_id}", response_model=UserOut)
async def get_user_profile(
    user_id: int,
    db: AsyncSession = Depends(get_async_session)
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    return user


# ============================================================
# 🔹 UPDATE PROFIL (PROTÉGÉ)
# ============================================================
@router.post("/update-profile", response_model=UserOut)
async def update_profile(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(require_completed_welcome),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    birth_date: Optional[date] = Form(None),
    avatar: Optional[UploadFile] = File(None),
):
    # 🔹 Mise à jour champs texte
    if first_name:
        current_user.first_name = first_name.strip()

    if last_name:
        current_user.last_name = last_name.strip()

    if phone:
        current_user.phone = phone.strip()

    if birth_date:
        current_user.birth_date = birth_date

    # ========================================================
    # 🔥 UPLOAD SÉCURISÉ
    # ========================================================
    if avatar:
        extension = os.path.splitext(avatar.filename)[1].lower()

        # ❌ extension invalide
        if extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Format de fichier non autorisé"
            )

        # ❌ taille fichier
        contents = await avatar.read()
        size_mb = len(contents) / (1024 * 1024)

        if size_mb > MAX_FILE_SIZE_MB:
            raise HTTPException(
                status_code=400,
                detail="Fichier trop volumineux (max 5MB)"
            )

        # 🔁 reset buffer
        avatar.file.seek(0)

        # 🔹 dossier
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        # 🔹 nom unique
        unique_filename = f"{uuid4().hex}{extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # 🔹 sauvegarde
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        # 🔹 URL publique
        current_user.avatar_url = f"{BACKEND_URL}/static/avatars/{unique_filename}"

    # ========================================================
    # 🔹 SAVE DB
    # ========================================================
    await db.commit()
    await db.refresh(current_user)

    return current_user