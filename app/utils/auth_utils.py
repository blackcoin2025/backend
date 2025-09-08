# app/utils/auth_utils.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User
from app.utils.token import verify_access_token

async def get_user_by_email(session: AsyncSession, email: str):
    res = await session.execute(select(User).where(User.email == email))
    return res.scalar_one_or_none()

async def get_user_by_username(session: AsyncSession, username: str):
    res = await session.execute(select(User).where(User.username == username))
    return res.scalar_one_or_none()
