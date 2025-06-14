# app/routers/status.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import UserStatus
from app.schemas import StatusBase, StatusOut

router = APIRouter(prefix="/status", tags=["Status"])

@router.get("/{telegram_id}", response_model=StatusOut)
async def get_status(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserStatus).where(UserStatus.telegram_id == telegram_id))
    status = result.scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    return status

@router.put("/{telegram_id}", response_model=StatusOut)
async def update_status(telegram_id: str, status_data: StatusBase, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UserStatus).where(UserStatus.telegram_id == telegram_id))
    status = result.scalar_one_or_none()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")
    
    for key, value in status_data.model_dump().items():
        setattr(status, key, value)
        
    await db.commit()
    await db.refresh(status)
    return status
