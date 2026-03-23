from sqlalchemy import Column,Integer,String,Boolean,DateTime,ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500))
    link = Column(String(255), nullable=False)
    validation_code = Column(String(10), nullable=False)
    reward_points = Column(Integer, default=0, nullable=False)
    reward_amount = Column(Integer, default=0, nullable=False)
    is_daily = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    logo = Column(String(100), nullable=True)


class UserTask(Base):
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())