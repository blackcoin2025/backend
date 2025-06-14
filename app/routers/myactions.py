# app/routers/myactions.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import MyAction
from app.schemas import MyActionBase, MyActionOut

router = APIRouter(prefix="/myactions", tags=["MyActions"])


@router.get("/{telegram_id}", response_model=list[MyActionOut])
async def get_user_actions(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MyAction).where(MyAction.telegram_id == telegram_id))
    actions = result.scalars().all()
    if not actions:
        raise HTTPException(status_code=404, detail="No actions found for this user.")
    return actions


@router.post("/", response_model=MyActionOut)
async def add_user_action(action_data: MyActionBase, db: AsyncSession = Depends(get_db)):
    new_action = MyAction(**action_data.model_dump())
    db.add(new_action)
    await db.commit()
    await db.refresh(new_action)
    return new_action


@router.delete("/{action_id}")
async def delete_user_action(action_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MyAction).where(MyAction.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found.")
    await db.delete(action)
    await db.commit()
    return {"detail": "Action deleted successfully"}
