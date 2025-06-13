from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TaskStat
from app.schemas import TaskBase  # On utilise TaskBase qui est bien défini dans schemas.py

router = APIRouter()


@router.get("/{telegram_id}")
def get_user_tasks(telegram_id: str, db: Session = Depends(get_db)):
    tasks = db.query(TaskStat).filter(TaskStat.telegram_id == telegram_id).first()
    if not tasks:
        raise HTTPException(status_code=404, detail="Tasks not found")
    return tasks


@router.put("/{telegram_id}")
def update_user_tasks(telegram_id: str, task_data: TaskBase, db: Session = Depends(get_db)):
    tasks = db.query(TaskStat).filter(TaskStat.telegram_id == telegram_id).first()
    if not tasks:
        raise HTTPException(status_code=404, detail="Tasks not found")

    for key, value in task_data.model_dump().items():
        setattr(tasks, key, value)

    db.commit()
    db.refresh(tasks)
    return tasks
