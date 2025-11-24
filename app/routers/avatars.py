import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from utils.avatar_generator import generate_avatar

router = APIRouter(prefix="/avatars", tags=["Avatars"])

AVATAR_UPLOAD_DIR = "static/uploads/avatars"      # Photos uploadées par l'utilisateur
GENERATED_DIR = "static/generated_avatars"        # Avatars générés automatiquement
DEFAULT_AVATAR = os.path.join(AVATAR_UPLOAD_DIR, "default.png")

# Assurer que les dossiers existent
os.makedirs(AVATAR_UPLOAD_DIR, exist_ok=True)
os.makedirs(GENERATED_DIR, exist_ok=True)


@router.get("/{username}", response_class=FileResponse)
async def get_user_avatar(username: str):
    """
    Retourne l'avatar d'un utilisateur selon cette logique :

    1️⃣ Si l’utilisateur a upload une vraie photo → renvoyer la photo réelle.
    2️⃣ Sinon → générer automatiquement un avatar basé sur son username.
    3️⃣ Si la génération échoue → renvoyer un avatar par défaut.
    """

    if not username:
        raise HTTPException(status_code=400, detail="Username manquant")

    # 1️⃣ Vérifier si une vraie photo existe (upload)
    uploaded_avatar = os.path.join(AVATAR_UPLOAD_DIR, f"{username}.png")
    if os.path.isfile(uploaded_avatar):
        return FileResponse(uploaded_avatar)

    # 2️⃣ Sinon → générer un avatar automatiquement
    try:
        generated_path = generate_avatar(username)
    except Exception:
        generated_path = None

    # Vérification si le fichier généré existe réellement
    if generated_path and os.path.isfile(generated_path):
        return FileResponse(generated_path)

    # 3️⃣ Si rien n’est disponible → fallback
    if os.path.isfile(DEFAULT_AVATAR):
        return FileResponse(DEFAULT_AVATAR)

    raise HTTPException(status_code=500, detail="Impossible de récupérer un avatar")
