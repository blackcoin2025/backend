from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class BaseMixin:
    """Mixins communs à toutes les tables"""
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class UserProfile(Base, BaseMixin):
    __tablename__ = "user_profiles"
    
    telegram_id = Column(String(50), unique=True, index=True, nullable=False)
    first_name = Column(String(100))
    username = Column(String(50), unique=True)
    photo_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime)

    __table_args__ = (
        {'comment': 'Stores user profile information from Telegram'},
    )


class Balance(Base, BaseMixin):
    __tablename__ = "balances"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), index=True, nullable=False)
    points = Column(BigInteger, default=0, nullable=False)
    coins = Column(BigInteger, default=0, nullable=False)

    __table_args__ = (
        {'comment': 'Tracks user points and coins balance'},
    )


class Level(Base, BaseMixin):
    __tablename__ = "levels"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), index=True, nullable=False)
    level = Column(Integer, default=1, nullable=False)
    xp = Column(BigInteger, default=0, nullable=False)
    xp_to_next_level = Column(BigInteger, default=1000)

    __table_args__ = (
        {'comment': 'User level progression system'},
    )


class Ranking(Base, BaseMixin):
    __tablename__ = "rankings"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), index=True, nullable=False)
    rank = Column(Integer, nullable=False)
    category = Column(String(50), default='global')

    __table_args__ = (
        Index('idx_ranking_category', 'category', 'rank'),
        {'comment': 'User rankings across different categories'},
    )


class TaskStat(Base, BaseMixin):
    __tablename__ = "task_stats"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), index=True, nullable=False)
    completed = Column(Integer, default=0, nullable=False)
    validated = Column(Integer, default=0, nullable=False)
    last_completed_at = Column(DateTime)

    __table_args__ = (
        {'comment': 'Tracks user task completion statistics'},
    )


class Friend(Base, BaseMixin):
    __tablename__ = "friends"
    
    inviter_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), nullable=False)
    invited_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), nullable=False)
    status = Column(String(20), default='pending')  # pending, accepted, blocked

    __table_args__ = (
        Index('idx_friend_pair', 'inviter_id', 'invited_id', unique=True),
        {'comment': 'Friendship relationships between users'},
    )


class Wallet(Base, BaseMixin):
    __tablename__ = "wallets"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), unique=True, nullable=False)
    ton_wallet_address = Column(String(128), unique=True, nullable=False)
    is_verified = Column(Boolean, default=False)

    __table_args__ = (
        {'comment': 'User cryptocurrency wallet information'},
    )


class UserAction(Base, BaseMixin):
    __tablename__ = "user_actions"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), index=True, nullable=False)
    action_type = Column(String(50), nullable=False)  # login, task_complete, etc.
    action_metadata = Column(JSON)

    __table_args__ = (
        Index('idx_action_type', 'action_type'),
        Index('idx_action_user_date', 'telegram_id', 'created_at'),
        {'comment': 'Log of important user actions'},
    )


class MyAction(Base, BaseMixin):
    __tablename__ = "my_actions"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), index=True, nullable=False)
    title = Column(String(100), nullable=False)
    description = Column(String(255))
    created_by = Column(String(50))  # ou un FK si nécessaire
    extra_data = Column(JSON, nullable=True)  # anciennement "metadata"

    __table_args__ = (
        Index('idx_myaction_user', 'telegram_id'),
        {'comment': 'Custom user-defined actions'},
    )


class UserStatus(Base, BaseMixin):
    __tablename__ = "user_status"
    
    telegram_id = Column(String(50), ForeignKey('user_profiles.telegram_id'), unique=True, nullable=False)
    status_text = Column(String(255))
    is_online = Column(Boolean, default=False)
    last_active = Column(DateTime)
    device_info = Column(String(255))

    __table_args__ = (
        {'comment': 'Current user status and activity information'},
    )
