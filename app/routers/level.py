from fastapi import APIRouter, HTTPException
from app.schemas import LevelBase, LevelOut

router = APIRouter(prefix="/level", tags=["level"])

# Exemple de route
@router.get("/{telegram_id}", response_model=LevelOut)
def get_user_level(telegram_id: str):
    # Ici tu mettras la logique réelle avec ta base de données
    return LevelOut(telegram_id=telegram_id, level=3, xp=120, xp_required=200)
