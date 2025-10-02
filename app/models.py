from sqlalchemy import Column, String, Integer, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

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

    # 🔥 Relation avec MiningHistory
    mining_histories = relationship("MiningHistory", back_populates="user", cascade="all, delete-orphan")

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
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())


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
    link = Column(String(255), nullable=False)   # ✅ lien de la tâche (vidéo, etc.)
    validation_code = Column(String(10), nullable=False)  # ✅ code de validation
    reward_points = Column(Integer, default=0, nullable=False)
    reward_amount = Column(Integer, default=0, nullable=False)
    is_daily = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    logo = Column(String(100), nullable=True)  # ✅ nom ou clé du logo que le front va utiliser

class UserTask(Base):
    __tablename__ = "user_tasks"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime, nullable=True)     # ⬅️ Quand l’utilisateur clique "Commencer"
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
