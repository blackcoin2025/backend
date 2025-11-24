from sqlalchemy import (
    Column,
    String,
    Integer,
    Date,
    Boolean,
    DateTime,
    ForeignKey,
    Float,
    Numeric,  # ✅ ajouté ici
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SqlEnum  # 👈 pour les enums SQLAlchemy
from app.database import Base
from datetime import datetime
import enum  # 👈 garde pour tes enums Python

# -----------------------------
# Utilisateurs en attente
# -----------------------------
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


# -----------------------------
# Utilisateurs validés
# -----------------------------
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

    # 🔧 Ajoute cette ligne :
    wallet = relationship("Wallet", back_populates="user", uselist=False, cascade="all, delete-orphan")

    # Relations existantes :
    mining_histories = relationship("MiningHistory", back_populates="user", cascade="all, delete-orphan")
    user_actions = relationship("UserAction", back_populates="user", cascade="all, delete-orphan")
    packs = relationship("UserPack", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.email}>"


# -----------------------------
# Codes promo
# -----------------------------
class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    code = Column(String(50), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    usage_limit = Column(Integer, default=0)
    used_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())


# -----------------------------
# Données complémentaires
# -----------------------------
class Wallet(Base):
    __tablename__ = "wallet"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    amount = Column(Numeric(10, 2), default=0.00, nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="wallet")

    
class Balance(Base):
    __tablename__ = "balance"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    points = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


class Friend(Base):
    __tablename__ = "friends"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    friend_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


# -----------------------------
# Tâches et actions
# -----------------------------
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


class Status(Base):
    __tablename__ = "status"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    message = Column(String(500), nullable=False)
    created_at = Column(DateTime, server_default=func.now())


# -----------------------------
# Mining et activités
# -----------------------------
class MineTimer(Base):
    __tablename__ = "minagetem"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    claimed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MiningHistory(Base):
    __tablename__ = "mining_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    points = Column(Integer, nullable=False)
    source = Column(String(50), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="mining_histories")

    def __repr__(self):
        return f"<MiningHistory user_id={self.user_id} points={self.points} source={self.source}>"


class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    streak = Column(Integer, default=1, nullable=False)
    last_checkin = Column(DateTime, server_default=func.now(), onupdate=func.now())


# -----------------------------
# Enums pour les Actions
# -----------------------------
class ActionType(enum.Enum):
    individuelle = "individuelle"
    commune = "commune"


class ActionStatus(enum.Enum):
    disponible = "disponible"
    complet = "complet"
    retire = "retire"


class ActionCategory(enum.Enum):
    finance = "finance"
    immobilier = "immobilier"
    opportunite = "opportunite"


# -----------------------------
# Actions (packs)
# -----------------------------
class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    category = Column(SqlEnum(ActionCategory), nullable=False)
    type = Column(SqlEnum(ActionType), default=ActionType.individuelle)
    total_parts = Column(Integer, default=1)
    price_per_part = Column(Float, nullable=False)
    value_bkc = Column(Float, nullable=True)
    image_url = Column(String(255), nullable=True)
    status = Column(SqlEnum(ActionStatus), default=ActionStatus.disponible)
    icon = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user_packs = relationship("UserPack", back_populates="pack", cascade="all, delete-orphan")
    daily_tasks = relationship("DailyTask", back_populates="pack", cascade="all, delete-orphan")
    buyers = relationship("UserAction", back_populates="action", cascade="all, delete-orphan")


class UserPack(Base):
    __tablename__ = "user_packs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pack_id = Column(Integer, ForeignKey("actions.id"), nullable=False)
    start_date = Column(DateTime, default=func.now())
    last_claim_date = Column(DateTime, nullable=True)
    daily_earnings = Column(Float, default=0)
    is_unlocked = Column(Boolean, default=False)
    total_earned = Column(Float, default=0)
    current_day = Column(Date, default=func.current_date())
    all_tasks_completed = Column(Boolean, default=False)
    pack_status = Column(String(50), default="payé")  # ✅ à ajouter ici

    user = relationship("User", back_populates="packs")
    pack = relationship("Action", back_populates="user_packs")
    tasks = relationship("UserDailyTask", back_populates="user_pack", cascade="all, delete-orphan")


class UserAction(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    action_id = Column(Integer, ForeignKey("actions.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, server_default=func.now())

    action = relationship("Action", back_populates="buyers")
    user = relationship("User", back_populates="user_actions")
    

class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id = Column(Integer, primary_key=True)
    pack_id = Column(Integer, ForeignKey("actions.id"), nullable=False)
    platform = Column(String(50))
    description = Column(String(255))
    video_url = Column(String(255))
    reward_share = Column(Float)

    pack = relationship("Action", back_populates="daily_tasks")
    user_tasks = relationship("UserDailyTask", back_populates="task", cascade="all, delete-orphan")


class UserDailyTask(Base):
    __tablename__ = "user_daily_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("daily_tasks.id"), nullable=False)
    user_pack_id = Column(Integer, ForeignKey("user_packs.id"), nullable=True)
    started_at = Column(DateTime, nullable=True)  # 🆕 ajouté
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)

    task = relationship("DailyTask", back_populates="user_tasks")
    user_pack = relationship("UserPack", back_populates="tasks")


# -----------------------------
# Bonus
# -----------------------------
class BonusStatus(enum.Enum):
    en_attente = "en_attente"
    eligible = "eligible"
    en_conversion = "en_conversion"
    converti = "converti"
    expire = "expire"


class Bonus(Base):
    __tablename__ = "bonus"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_points = Column(Float, default=0.0, nullable=False)
    points_restants = Column(Float, default=0.0, nullable=False)
    pourcentage_conversion = Column(Float, default=0.05, nullable=False)
    valeur_equivalente = Column(Float, nullable=True)
    status = Column(SqlEnum(BonusStatus), default=BonusStatus.en_attente, nullable=False)
    raison = Column(String(100), default="bonus_inscription", nullable=False)
    cree_le = Column(DateTime, server_default=func.now())
    converti_le = Column(DateTime, nullable=True)

    user = relationship("User", backref="bonus")
