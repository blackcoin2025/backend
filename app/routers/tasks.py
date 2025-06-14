# app/routers/taskstat.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models import TaskStat
from app.schemas import TaskBase, TaskOut

router = APIRouter(prefix="/tasks", tags=["Tasks"])

@router.get("/{telegram_id}", response_model=TaskOut)
async def get_user_tasks(telegram_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskStat).where(TaskStat.telegram_id == telegram_id))
    tasks = result.scalar_one_or_none()
    if not tasks:
        raise HTTPException(status_code=404, detail="Tasks not found")
    return tasks

@router.put("/{telegram_id}", response_model=TaskOut)
async def update_user_tasks(telegram_id: str, task_data: TaskBase, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskStat).where(TaskStat.telegram_id == telegram_id))
    tasks = result.scalar_one_or_none()
    if not tasks:
        raise HTTPException(status_code=404, detail="Tasks not found")

    for key, value in task_data.model_dump().items():
        setattr(tasks, key, value)

    await db.commit()
    await db.refresh(tasks)
    return tasks
