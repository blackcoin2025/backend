from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.security import HTTPBearer
from app.services.telegram_auth import verify_telegram_auth_data
from app.models import UserProfile
from app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas import TelegramInitData, UserOut
import logging
from typing import Optional

router = APIRouter(prefix="/auth", tags=["Auth"])
security = HTTPBearer()
logger = logging.getLogger(__name__)

@router.post(
    "/telegram/init",
    response_model=dict,
    responses={
        200: {"description": "Authentification réussie"},
        401: {"description": "Signature Telegram invalide"},
        500: {"description": "Erreur serveur"}
    }
)
async def telegram_init(
    data: TelegramInitData,
    db: AsyncSession = Depends(get_db),
    request: Request
) -> dict:
    """
    Authentifie un utilisateur via Telegram et crée/mets à jour son profil.
    
    Args:
        data: Données d'authentification Telegram validées
        db: Session de base de données async
        request: Requête HTTP pour logging
    
    Returns:
        dict: {isNew: bool, user: UserOut}
    
    Raises:
        HTTPException: En cas d'erreur d'authentification ou serveur
    """
    # Log structuré avec des données sensibles masquées
    logger.info(
        "Tentative d'authentification Telegram",
        extra={
            "telegram_id": data.user.id,
            "username": data.user.username,
            "auth_date": data.auth_date
        }
    )
    
    # Validation des données Telegram
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
        logger.warning("Signature Telegram invalide reçue")
        raise HTTPException(
            status_code=401,
            detail="Signature Telegram invalide"
        )

    telegram_id = str(data.user.id)

    try:
        # Recherche de l'utilisateur existant
        user: Optional[UserProfile] = await _get_user_by_telegram_id(db, telegram_id)
        
        if user:
            logger.info(f"Utilisateur existant connecté: {telegram_id}")
            return {
                "isNew": False,
                "user": UserOut.model_validate(user)
            }

        # Création d'un nouvel utilisateur
        new_user = await _create_telegram_user(db, telegram_id, data)
        logger.info(f"Nouvel utilisateur créé: {telegram_id}")
        
        return {
            "isNew": True,
            "user": UserOut.model_validate(new_user)
        }

    except Exception as e:
        logger.error(f"Erreur lors de l'authentification Telegram: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erreur lors du traitement de l'authentification"
        ) from e

async def _get_user_by_telegram_id(
    db: AsyncSession, 
    telegram_id: str
) -> Optional[UserProfile]:
    """Helper pour récupérer un utilisateur par son Telegram ID"""
    result = await db.execute(
        select(UserProfile)
        .where(UserProfile.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()

async def _create_telegram_user(
    db: AsyncSession,
    telegram_id: str,
    data: TelegramInitData
) -> UserProfile:
    """Helper pour créer un nouvel utilisateur Telegram"""
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