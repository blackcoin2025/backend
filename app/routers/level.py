from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import Level
from app.schemas import LevelBase, LevelOut

router = APIRouter(prefix="/level", tags=["Level"])

# 🔹 GET - Récupérer les infos de niveau d’un utilisateur
@router.get("/{telegram_id}", response_model=LevelOut)
async def get_user_level(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Level).where(Level.telegram_id == telegram_id))
    level = result.scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found for this user.")
    return level

# 🔹 POST - Créer un nouveau niveau pour un utilisateur
@router.post("/", response_model=LevelOut)
async def create_user_level(level_data: LevelBase, db: AsyncSession = Depends(get_db)):
    # Vérifie s'il existe déjà une ligne pour cet utilisateur
    result = await db.execute(select(Level).where(Level.telegram_id == level_data.telegram_id))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Level already exists for this user.")
    
    new_level = Level(**level_data.model_dump())
    db.add(new_level)
    await db.commit()
    await db.refresh(new_level)
    return new_level

# 🔹 PUT - Mettre à jour le niveau d’un utilisateur
@router.put("/{telegram_id}", response_model=LevelOut)
async def update_user_level(telegram_id: str, level_data: LevelBase, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Level).where(Level.telegram_id == telegram_id))
    level = result.scalar_one_or_none()
    if not level:
        raise HTTPException(status_code=404, detail="Level not found.")

    for key, value in level_data.model_dump().items():
        setattr(level, key, value)
    
    await db.commit()
    await db.refresh(level)
    return level
