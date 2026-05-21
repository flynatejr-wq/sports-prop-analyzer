"""User picks and bankroll tracking."""
import enum
from typing import Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.prop import PropResult


class BetDirection(str, enum.Enum):
    OVER = "over"
    UNDER = "under"


class UserPick(Base):
    __tablename__ = "user_picks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prop_id: Mapped[int] = mapped_column(Integer, ForeignKey("props.id"), index=True)
    direction: Mapped[BetDirection] = mapped_column(SAEnum(BetDirection))
    stake: Mapped[float] = mapped_column(Float)          # units wagered
    odds: Mapped[Optional[float]] = mapped_column(Float) # odds at time of pick
    ev_at_pick: Mapped[Optional[float]] = mapped_column(Float)
    result: Mapped[PropResult] = mapped_column(SAEnum(PropResult), default=PropResult.PENDING)
    profit_loss: Mapped[Optional[float]] = mapped_column(Float)
    notes: Mapped[Optional[str]] = mapped_column(String(500))

    prop: Mapped["Prop"] = relationship("Prop", back_populates="user_picks")
