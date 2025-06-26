# app/models.py

from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func

# Base SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass

# Mixin de base (id, created_at, updated_at)
class BaseMixin:
    id = Column(String, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# -------------------------------
# ✅ Modèle unique : UserProfile
# -------------------------------

class UserProfile(Base):
    __tablename__ = "user_profiles"

    telegram_id = Column(String(50), primary_key=True, index=True, unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    username = Column(String(50), unique=True, nullable=True)
    photo_url = Column(String(255), nullable=True)

    __table_args__ = (
        {'comment': 'Minimal user info from Telegram for authentication'},
    )
