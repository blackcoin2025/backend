# app/services/avatar_update.py

import os
import shutil
from typing import Optional
from fastapi import UploadFile
from sqlalchemy import select
from app.models import User
from app.database import AsyncSessionLocal

# ============================================================
# 🌐 Configuration
# ============================================================

RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")
BACKEND_URL = (RENDER_EXTERNAL_URL or os.getenv("BACKEND_URL", "http://localhost:8000")).rstrip("/")
UPLOAD_DIR = os.path.join("static", "uploads", "avatars")

# Création automatique du dossier si inexistant
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ============================================================
# 🔹 Utilitaires
# ============================================================

def make_public_url(path: Optional[str]) -> Optional[str]:
    """Convertit un chemin local ou relatif en URL publique absolue."""
    if not path:
        return None
    if path.startswith("http"):
        return path
    if path.startswith("/"):
        return f"{BACKEND_URL}{path}"
    return f"{BACKEND_URL}/{path}"

# ============================================================
# 🎨 Génération et gestion des avatars
# ============================================================

async def generate_default_avatar(user: User) -> str:
    """
    Génére un avatar par défaut seulement si l'utilisateur n'en a pas déjà un.
    Empêche d'écraser un avatar uploadé.
    """
    # 🔒 Empêche l’écrasement d’un avatar déjà existant
    if user.avatar_url and not user.avatar_url.endswith("default.png"):
        print(f"ℹ️ L'utilisateur {user.id} a déjà un avatar, on ne remplace pas.")
        return user.avatar_url

    filename = f"default_{user.id}.png"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Copie du modèle de base
    template = os.path.join("static", "default.png")
    if os.path.exists(template):
        shutil.copy(template, file_path)
    else:
        # Crée un fichier vide si le modèle est absent (sécurité)
        open(file_path, "wb").close()

    avatar_url = f"/{file_path.replace(os.sep, '/')}"
    public_url = make_public_url(avatar_url)

    # Mise à jour en base
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user.id))
        db_user = result.scalars().first()
        if db_user:
            db_user.avatar_url = public_url
            await session.commit()

    print(f"✅ Avatar par défaut créé pour user_id={user.id}")
    return public_url


async def get_avatar(user_id: int) -> Optional[str]:
    """Récupère l’URL publique de l’avatar d’un utilisateur."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            return None
        return make_public_url(user.avatar_url)


async def update_avatar(user_id: int, file: UploadFile) -> Optional[str]:
    """Met à jour l’avatar d’un utilisateur avec un nouveau fichier uploadé."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            print(f"⚠️ Aucun utilisateur trouvé pour id={user_id}")
            return None

        # Supprime l'ancien avatar s'il est local
        if user.avatar_url and user.avatar_url.startswith(BACKEND_URL):
            local_path = user.avatar_url.replace(BACKEND_URL, "").lstrip("/")
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except Exception as e:
                    print(f"⚠️ Erreur suppression ancien avatar: {e}")

        # Sauvegarde du nouveau fichier
        filename = f"user_{user_id}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        avatar_url = f"/{file_path.replace(os.sep, '/')}"
        public_url = make_public_url(avatar_url)

        # Mise à jour en base
        user.avatar_url = public_url
        await session.commit()

        print(f"✅ Avatar mis à jour pour user_id={user_id}")
        return public_url


async def rebuild_avatar_url(avatar_url: Optional[str]) -> Optional[str]:
    """Reconstruit proprement une URL publique à partir d’un chemin local."""
    if not avatar_url:
        return None
    if avatar_url.startswith("http"):
        return avatar_url
    if not avatar_url.startswith("/"):
        avatar_url = f"/{avatar_url}"
    return f"{BACKEND_URL}{avatar_url}"

# ============================================================
# 💾 Sauvegarde générique d'un avatar uploadé
# ============================================================

async def save_upload_file(file: UploadFile, user_id: Optional[int] = None) -> str:
    """Sauvegarde un fichier d'avatar uploadé et retourne son chemin relatif."""
    if not file:
        raise ValueError("Aucun fichier uploadé fourni")

    if file.content_type not in ["image/jpeg", "image/png"]:
        raise ValueError("Format d'image non supporté (JPEG/PNG uniquement)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    base_name = os.path.basename(file.filename)
    safe_name = f"user_{user_id or 'anon'}_{base_name}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    rel_path = f"/{file_path.replace(os.sep, '/')}"
    return rel_path


async def update_single_avatar(user_id: int):
    """Met à jour uniquement le format de l’URL d’un utilisateur si besoin."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()
        if not user:
            print(f"⚠️ Aucun utilisateur trouvé avec id={user_id}")
            return None

        if not user.avatar_url:
            print(f"ℹ️ L’utilisateur {user_id} n’a pas d’avatar.")
            return None

        new_url = await rebuild_avatar_url(user.avatar_url)
        if new_url != user.avatar_url:
            user.avatar_url = new_url
            await session.commit()
            print(f"✅ Avatar normalisé pour user_id={user_id}")
        else:
            print(f"ℹ️ Avatar déjà correct pour {user_id}")

        return user.avatar_url
