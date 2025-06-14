# app/routers/actions.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import MyAction
from app.schemas import ActionBase, ActionOut

router = APIRouter(prefix="/actions", tags=["Actions"])


@router.get("/{telegram_id}", response_model=list[ActionOut])
async def get_actions(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MyAction).where(MyAction.telegram_id == telegram_id))
    actions = result.scalars().all()
    if not actions:
        raise HTTPException(status_code=404, detail="No actions found for this user.")
    return actions


@router.post("/", response_model=ActionOut)
async def create_action(action_data: ActionBase, db: AsyncSession = Depends(get_db)):
    new_action = MyAction(**action_data.model_dump())
    db.add(new_action)
    await db.commit()
    await db.refresh(new_action)
    return new_action
