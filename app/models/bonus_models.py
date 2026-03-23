from sqlalchemy import Column,Integer,String,DateTime,ForeignKey,Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SqlEnum
from sqlalchemy.sql import func
from decimal import Decimal
import enum
from app.database import Base


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

    total_points = Column(Numeric(18, 6), default=Decimal("0"), nullable=False)
    points_restants = Column(Numeric(18, 6), default=Decimal("0"), nullable=False)
    pourcentage_conversion = Column(Numeric(10, 6), default=Decimal("0.05"), nullable=False)
    valeur_equivalente = Column(Numeric(18, 6), nullable=True)

    status = Column(SqlEnum(BonusStatus), default=BonusStatus.en_attente, nullable=False)
    raison = Column(String(100), default="bonus_inscription", nullable=False)

    cree_le = Column(DateTime, server_default=func.now())
    converti_le = Column(DateTime, nullable=True)
    last_claim_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="bonus")


class RealCash(Base):
    __tablename__ = "real_cash"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    cash_balance = Column(Numeric(12,2), default=0.00, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="real_cash")