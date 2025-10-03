from fastapi import APIRouter, Depends, HTTPException, Form, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from datetime import date
import os
import shutil
from uuid import uuid4

from app.database import get_async_session
from app.dependencies.auth import get_current_user
from app.models import User
from app.schemas import UserOut

# ✅ Récupérer la variable d'environnement pour l'URL du backend
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """
    Retourne le profil de l'utilisateur actuellement connecté.
    """
    return current_user


@router.get("/{user_id}", response_model=UserOut)
async def get_user_profile(user_id: int, db: AsyncSession = Depends(get_async_session)):
    """
    Récupère le profil public d'un utilisateur à partir de son ID.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur non trouvé")

    return user


@router.post("/update-profile", response_model=UserOut)
async def update_profile(
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
    first_name: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    birth_date: Optional[date] = Form(None),
    avatar: Optional[UploadFile] = File(None),
):
    """
    Met à jour les informations de profil de l'utilisateur connecté, y compris la photo de profil.
    """

    # 🔹 Mise à jour des champs texte
    if first_name:
        current_user.first_name = first_name
    if last_name:
        current_user.last_name = last_name
    if phone:
        current_user.phone = phone
    if birth_date:
        current_user.birth_date = birth_date

    # 🔹 Gestion de la photo de profil
    if avatar:
        extension = os.path.splitext(avatar.filename)[1]
        unique_filename = f"{uuid4().hex}{extension}"

        upload_dir = "static/avatars"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, unique_filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(avatar.file, buffer)

        # ✅ Génère une URL publique complète
        current_user.avatar_url = f"{BACKEND_URL}/static/avatars/{unique_filename}"

    await db.commit()
    await db.refresh(current_user)

    return current_user
