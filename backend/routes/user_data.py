from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from backend.database import get_db
from backend.models import User, Profile, Wallet
from backend.schemas import UserDataOut, UpdateUserData

router = APIRouter(prefix="/user", tags=["Utilisateur"])

# ---------------- GET: récupérer toutes les infos utilisateur ----------------

@router.get("/{telegram_id}", response_model=UserDataOut)
async def get_user_data(telegram_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()
    if not user or not user.is_verified:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable ou non vérifié.")

    return UserDataOut(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        telegram_username=user.telegram_username,
        telegram_id=user.telegram_id,
        telegram_photo=user.telegram_photo,
        profile=user.profile,
        wallet=user.wallet
    )

# ---------------- PUT: mise à jour du profil utilisateur ----------------

@router.put("/update/{telegram_id}")
async def update_user_data(telegram_id: int, updates: UpdateUserData, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    # Mise à jour du profil
    for key, value in updates.dict(exclude_unset=True).items():
        if hasattr(user.profile, key):
            setattr(user.profile, key, value)
        elif hasattr(user.wallet, key):
            setattr(user.wallet, key, value)
        else:
            raise HTTPException(status_code=400, detail=f"Champ invalide : {key}")

    await db.commit()
    return {"detail": "Données utilisateur mises à jour avec succès."}
