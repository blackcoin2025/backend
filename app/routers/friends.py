# app/routers/friends.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import Friend
from app.schemas import FriendBase, FriendOut

router = APIRouter(prefix="/friends", tags=["Friends"])

@router.post("/", response_model=FriendOut)
async def add_friend(friend_data: FriendBase, db: AsyncSession = Depends(get_db)):
    new_friend = Friend(**friend_data.dict())
    db.add(new_friend)
    await db.commit()
    await db.refresh(new_friend)
    return new_friend

@router.get("/{telegram_id}", response_model=list[FriendOut])
async def get_friends(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Friend).where(Friend.inviter_id == telegram_id))
    return result.scalars().all()
