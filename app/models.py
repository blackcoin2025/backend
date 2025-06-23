from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    BigInteger, JSON, Index, CheckConstraint
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

# Constantes
TELEGRAM_ID_LEN = 50
USERNAME_LEN = 50
EMAIL_LEN = 100
PHONE_LEN = 20

# Base SQLAlchemy 2.0
class Base(DeclarativeBase):
    pass

# Mixin de base
class BaseMixin:
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ----------------------
# TABLES PRINCIPALES
# ----------------------

class UserProfile(Base, BaseMixin):
    __tablename__ = "user_profiles"

    telegram_id = Column(String(TELEGRAM_ID_LEN), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100))
    username = Column(String(USERNAME_LEN), unique=True)
    photo_url = Column(String(255))
    email = Column(String(EMAIL_LEN), unique=True, nullable=True)
    phone = Column(String(PHONE_LEN), nullable=True)
    birth_date = Column(String(20), nullable=True)  # ISO string format
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime)

    # Relations
    balance = relationship("Balance", uselist=False, backref="user", cascade="all, delete-orphan")
    level = relationship("Level", uselist=False, backref="user", cascade="all, delete-orphan")
    wallet = relationship("Wallet", uselist=False, backref="user", cascade="all, delete-orphan")
    status = relationship("UserStatus", uselist=False, backref="user", cascade="all, delete-orphan")

    __table_args__ = (
        {'comment': 'Stores user profile information from Telegram'},
    )

class Balance(Base, BaseMixin):
    __tablename__ = "balances"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    points = Column(BigInteger, default=0, nullable=False)
    coins = Column(BigInteger, default=0, nullable=False)

    __table_args__ = (
        CheckConstraint("points >= 0", name="check_points_positive"),
        {'comment': 'Tracks user points and coins balance'},
    )

class Level(Base, BaseMixin):
    __tablename__ = "levels"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    xp = Column(BigInteger, default=0, nullable=False)
    xp_to_next_level = Column(BigInteger, default=1000)

    __table_args__ = (
        {'comment': 'User level progression system'},
    )

class Ranking(Base, BaseMixin):
    __tablename__ = "rankings"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    rank = Column(Integer, nullable=False)
    category = Column(String(50), default="global")

    __table_args__ = (
        Index('idx_ranking_category', 'category', 'rank'),
        {'comment': 'User rankings across different categories'},
    )

class TaskStat(Base, BaseMixin):
    __tablename__ = "task_stats"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    completed = Column(Integer, default=0, nullable=False)
    validated = Column(Integer, default=0, nullable=False)
    last_completed_at = Column(DateTime)

    __table_args__ = (
        {'comment': 'Tracks user task completion statistics'},
    )

class Friend(Base, BaseMixin):
    __tablename__ = "friends"

    inviter_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), nullable=False)
    invited_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default='pending')

    __table_args__ = (
        Index('idx_friend_pair', 'inviter_id', 'invited_id', unique=True),
        {'comment': 'Friendship relationships between users'},
    )

class Wallet(Base, BaseMixin):
    __tablename__ = "wallets"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), unique=True, nullable=False)
    ton_wallet_address = Column(String(128), unique=True, nullable=False)
    is_verified = Column(Boolean, default=False)
    balance = Column(BigInteger, default=0, nullable=False)  # ← 👈 Ajoute ceci

    __table_args__ = (
        {'comment': 'User cryptocurrency wallet information'},
    )

class UserAction(Base, BaseMixin):
    __tablename__ = "user_actions"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    action_type = Column(String(50), nullable=False)
    action_metadata = Column(JSON)

    __table_args__ = (
        Index('idx_action_type', 'action_type'),
        Index('idx_action_user_date', 'telegram_id', 'created_at'),
        {'comment': 'Log of important user actions'},
    )

class MyAction(Base, BaseMixin):
    __tablename__ = "my_actions"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String(255))
    created_by = Column(String(50))  # ou FK
    extra_data = Column(JSON)

    __table_args__ = (
        Index('idx_myaction_user', 'telegram_id'),
        {'comment': 'Custom user-defined actions'},
    )

class UserStatus(Base, BaseMixin):
    __tablename__ = "user_status"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), unique=True, nullable=False)
    status_text = Column(String(255))
    is_online = Column(Boolean, default=False)
    last_active = Column(DateTime)
    device_info = Column(String(255))

    __table_args__ = (
        {'comment': 'Current user status and activity information'},
    )

# ✅ CORRECT : en dehors de toute autre classe
class WelcomeTask(Base, BaseMixin):
    __tablename__ = "welcome_tasks"

    telegram_id = Column(String(TELEGRAM_ID_LEN), ForeignKey("user_profiles.telegram_id", ondelete="CASCADE"), index=True, nullable=False)
    task_name = Column(String(100), nullable=False)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime)

    __table_args__ = (
        Index('idx_welcome_task_user', 'telegram_id'),
        {'comment': 'Welcome tasks (onboarding) completed by users'},
    )

    user = relationship("UserProfile", backref="welcome_tasks")
