import enum
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SqlEnum
from app.database import Base


# -----------------------------
# ENUMS (CLÉS TECHNIQUES)
# -----------------------------
class ActionType(str, enum.Enum):
    individual = "individual"
    shared = "shared"


class ActionStatus(str, enum.Enum):
    available = "available"
    completed = "completed"
    withdrawn = "withdrawn"


class ActionCategory(str, enum.Enum):
    finance = "finance"
    real_estate = "real_estate"
    opportunity = "opportunity"


class PackStatus(str, enum.Enum):
    paid = "paid"
    in_progress = "in_progress"
    on_hold = "on_hold"

# -----------------------------
# ACTIONS (PACKS)
# -----------------------------
class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)

    # 🔥 clé i18n (ex: "discovery")
    name = Column(String(150), nullable=False)

    category = Column(SqlEnum(ActionCategory), nullable=False)

    type = Column(
        SqlEnum(ActionType),
        default=ActionType.individual,
        nullable=False
    )

    total_parts = Column(Integer, default=1)

    price_per_part = Column(Float, nullable=False)
    price_usdt = Column(Float, nullable=False)

    value_LTN = Column(Float, nullable=True)
    image_url = Column(String(255), nullable=True)

    status = Column(
        SqlEnum(ActionStatus),
        default=ActionStatus.available,
        nullable=False
    )

    created_at = Column(DateTime, server_default=func.now())

    # relations
    user_packs = relationship(
        "UserPack",
        back_populates="pack",
        cascade="all, delete-orphan"
    )

    daily_tasks = relationship(
        "DailyTask",
        back_populates="pack",
        cascade="all, delete-orphan"
    )

    buyers = relationship(
        "UserAction",
        back_populates="action",
        cascade="all, delete-orphan"
    )


# -----------------------------
# USER PACK
# -----------------------------
class UserPack(Base):
    __tablename__ = "user_packs"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    pack_id = Column(Integer, ForeignKey("actions.id"), nullable=False)

    # 📅 Dates
    start_date = Column(DateTime(timezone=True), default=func.now())
    last_claim_date = Column(DateTime(timezone=True), nullable=True)

    # 💰 Gains
    daily_earnings = Column(Float, default=0)
    total_earned = Column(Float, default=0)

    # 🔓 état interne
    is_unlocked = Column(Boolean, default=False)

    # 📆 gestion journalière
    current_day = Column(Date, default=func.current_date())
    all_tasks_completed = Column(Boolean, default=False)

    # 🔥 STATUS PROPRE (ENUM)
    pack_status = Column(
        SqlEnum(PackStatus),
        default=PackStatus.paid,
        nullable=False
    )

    # relations
    user = relationship("User", back_populates="packs")
    pack = relationship("Action", back_populates="user_packs")

    tasks = relationship(
        "UserDailyTask",
        back_populates="user_pack",
        cascade="all, delete-orphan"
    )

# -----------------------------
# USER ACTION (ACHAT)
# -----------------------------
class UserAction(Base):
    __tablename__ = "user_actions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    action_id = Column(
        Integer,
        ForeignKey("actions.id", ondelete="CASCADE"),
        nullable=False
    )

    quantity = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)

    timestamp = Column(DateTime, server_default=func.now())

    action = relationship("Action", back_populates="buyers")
    user = relationship("User", back_populates="user_actions")


# -----------------------------
# DAILY TASK
# -----------------------------
class DailyTask(Base):
    __tablename__ = "daily_tasks"

    id = Column(Integer, primary_key=True)

    pack_id = Column(Integer, ForeignKey("actions.id"), nullable=False)

    # 🔥 clés i18n
    platform = Column(String(50))      # ex: "telegram"
    description = Column(String(255))  # ex: "join_telegram"

    video_url = Column(String(255))

    reward_share = Column(Float)

    pack = relationship("Action", back_populates="daily_tasks")

    user_tasks = relationship(
        "UserDailyTask",
        back_populates="task",
        cascade="all, delete-orphan"
    )


# -----------------------------
# USER DAILY TASK
# -----------------------------

class UserDailyTask(Base):
    __tablename__ = "user_daily_tasks"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    task_id = Column(Integer, ForeignKey("daily_tasks.id"), nullable=False)

    user_pack_id = Column(Integer, ForeignKey("user_packs.id"), nullable=True)

    # ✅ FIX ICI
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    task = relationship("DailyTask", back_populates="user_tasks")
    user_pack = relationship("UserPack", back_populates="tasks")