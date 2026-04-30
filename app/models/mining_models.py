from sqlalchemy import Column, Integer, BigInteger, String, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class MineTimer(Base):
    __tablename__ = "minagetem"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # ✅ CRITIQUE
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    claimed = Column(Boolean, default=False, nullable=False)

    # ✅ recommandé
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MiningHistory(Base):
    __tablename__ = "mining_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    points = Column(Integer, nullable=False)
    source = Column(String(50), nullable=True)

    # ✅ recommandé
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="mining_histories")


class DailyCheckIn(Base):
    __tablename__ = "daily_checkins"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    date = Column(Date, nullable=False)  # OK (pas concerné)
    streak = Column(Integer, default=1, nullable=False)

    # ⚠️ utilisé pour logique → mieux en timezone
    last_checkin = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class UserMiningStats(Base):
    __tablename__ = "user_mining_stats"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    total_mined = Column(BigInteger, nullable=False, default=0)
    level = Column(Integer, nullable=False, default=1)

    # ✅ recommandé
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="mining_stats", uselist=False)