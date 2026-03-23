from sqlalchemy import Column,String,Integer,Date,Boolean,DateTime,ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class PendingUser(Base):
    __tablename__ = "pending_users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(30), unique=True, index=True, nullable=False)
    avatar_url = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    promo_code_used = Column(String(50), nullable=True)
    verification_code = Column(String(6), nullable=False)
    code_expires_at = Column(DateTime, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<PendingUser {self.email}>"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    birth_date = Column(Date, nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    username = Column(String(30), unique=True, index=True, nullable=False)
    avatar_url = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    has_completed_welcome_tasks = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")
    mining_histories = relationship("MiningHistory", back_populates="user", cascade="all, delete-orphan")
    user_actions = relationship("UserAction", back_populates="user", cascade="all, delete-orphan")
    packs = relationship("UserPack", back_populates="user", cascade="all, delete-orphan")
    mining_stats = relationship("UserMiningStats", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    usage_limit = Column(Integer, default=0)
    used_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())