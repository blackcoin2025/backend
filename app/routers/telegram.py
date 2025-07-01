from fastapi import APIRouter, HTTPException, Depends
from app.services.telegram_auth import verify_telegram_auth_data
from app.models import UserProfile
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from urllib.parse import parse_qsl
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])

@router.post("/telegram/init")
async def telegram_init(payload: dict, db: AsyncSession = Depends(get_db)):
    init_data = payload.get("initData")
    if not init_data:
        raise HTTPException(status_code=400, detail="initData manquant")

    # Convertit initData (ex: "id=...&first_name=...") en dict
    auth_data = dict(parse_qsl(init_data, keep_blank_values=True))

    if not verify_telegram_auth_data(auth_data):
        raise HTTPException(status_code=401, detail="Signature Telegram invalide")

    telegram_id = auth_data["id"]

    try:
        # 1. Recherche de l’utilisateur
        result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
        user = result.scalar_one_or_none()

        if user:
            return {
                "isNew": False,
                "user": UserOut.model_validate(user)
            }

        # 2. Création du nouvel utilisateur
        new_user = UserProfile(
            telegram_id=telegram_id,
            first_name=auth_data.get("first_name"),
            last_name=auth_data.get("last_name"),
            username=auth_data.get("username"),
            photo_url=auth_data.get("photo_url"),
        )

        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return {
            "isNew": True,
            "user": UserOut.model_validate(new_user)
        }

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)}")
