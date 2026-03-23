from sqlalchemy import Column,Integer,BigInteger,DateTime,ForeignKey,Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from decimal import Decimal
from app.database import Base


class Wallet(Base):
    __tablename__ = "wallet"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    amount = Column(
        Numeric(10, 2, asdecimal=True),
        nullable=False,
        default=Decimal("0.00"),
        server_default="0.00",
    )

    last_updated = Column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship(
        "User",
        back_populates="wallet",
        uselist=False,
    )

    def get_balance(self):
        return self.amount or Decimal("0.00")


class Balance(Base):
    __tablename__ = "balance"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    points = Column(BigInteger, default=0, nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())