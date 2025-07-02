from fastapi import APIRouter, HTTPException, Depends, Request
from app.services.telegram_auth import verify_telegram_auth_data
from app.models import UserProfile
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas import TelegramInitData, UserOut, TelegramAuthResponse
from typing import Optional
import logging

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

@router.post(
    "/telegram/init",
    response_model=TelegramAuthResponse,
    responses={
        200: {"description": "Authentification réussie"},
        401: {"description": "Signature Telegram invalide"},
        500: {"description": "Erreur serveur"}
    }
)
async def telegram_init(
    request: Request,  # ✅ Doit venir AVANT les arguments avec `=`
    data: TelegramInitData,
    db: AsyncSession = Depends(get_db),
) -> TelegramAuthResponse:
    """
    Authentifie un utilisateur via Telegram et crée/mets à jour son profil.
    """
    logger.info(
        f"🔐 Authentification Telegram pour user_id={data.user.id}, username={data.user.username}"
    )

    # 🔍 Debug brut
    raw_body = await request.body()
    print("📦 Payload JSON brut:", raw_body.decode())

    # Signature HMAC
    auth_data = {
        "id": data.user.id,
        "first_name": data.user.first_name,
        "last_name": data.user.last_name,
        "username": data.user.username,
        "photo_url": data.user.photo_url,
        "auth_date": data.auth_date,
        "hash": data.hash
    }

    if not verify_telegram_auth_data(auth_data):
        logger.warning("❌ Signature Telegram invalide")
        raise HTTPException(status_code=401, detail="Signature Telegram invalide")

    telegram_id = str(data.user.id)

    try:
        # Rechercher l'utilisateur
        user = await _get_user_by_telegram_id(db, telegram_id)
        if user:
            logger.info(f"✅ Utilisateur existant connecté: {telegram_id}")
            return TelegramAuthResponse(isNew=False, user=UserOut.model_validate(user))

        # Créer un nouvel utilisateur
        new_user = await _create_telegram_user(db, telegram_id, data)
        logger.info(f"🆕 Nouvel utilisateur créé: {telegram_id}")

        return TelegramAuthResponse(isNew=True, user=UserOut.model_validate(new_user))

    except Exception as e:
        logger.error(f"⚠️ Erreur serveur lors de l'auth Telegram: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Erreur lors de l'authentification") from e

# 🔧 Helpers
async def _get_user_by_telegram_id(db: AsyncSession, telegram_id: str) -> Optional[UserProfile]:
    result = await db.execute(select(UserProfile).where(UserProfile.telegram_id == telegram_id))
    return result.scalar_one_or_none()

async def _create_telegram_user(db: AsyncSession, telegram_id: str, data: TelegramInitData) -> UserProfile:
    new_user = UserProfile(
        telegram_id=telegram_id,
        first_name=data.user.first_name,
        last_name=data.user.last_name,
        username=data.user.username,
        photo_url=data.user.photo_url,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
