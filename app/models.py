from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class UserProfile(Base):
    __tablename__ = "user_profiles"

    telegram_id = Column(String(50), primary_key=True, index=True, unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=True)
    username = Column(String(50), unique=True, nullable=True)
    photo_url = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        {'comment': 'Minimal user info from Telegram for authentication'},
    )
