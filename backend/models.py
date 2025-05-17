from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_username = Column(String, unique=True, index=True, nullable=False)
    telegram_id = Column(String, unique=True, nullable=True)
    telegram_photo = Column(String, nullable=True)

    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relations
    profile = relationship("Profile", back_populates="user", uselist=False)
    wallet = relationship("Wallet", back_populates="user", uselist=False)
    email_verification = relationship("EmailVerificationCode", back_populates="user", uselist=False)


class EmailVerificationCode(Base):
    __tablename__ = "email_verification_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    code = Column(String(6), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="email_verification")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    level = Column(Integer, default=1)
    points = Column(Integer, default=0)
    ranking = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)

    user = relationship("User", back_populates="profile")


class Wallet(Base):
    __tablename__ = "wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    balance = Column(Integer, default=0)

    user = relationship("User", back_populates="wallet")
