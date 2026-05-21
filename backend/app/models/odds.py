"""Odds history and sportsbook line tracking."""
from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class OddsSnapshot(Base):
    """Point-in-time snapshot of odds across sportsbooks for a prop."""
    __tablename__ = "odds_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prop_id: Mapped[int] = mapped_column(Integer, ForeignKey("props.id", ondelete="CASCADE"), index=True)
    sportsbook: Mapped[str] = mapped_column(String(100))
    line: Mapped[float] = mapped_column(Float)
    over_odds: Mapped[Optional[float]] = mapped_column(Float)
    under_odds: Mapped[Optional[float]] = mapped_column(Float)
    is_live: Mapped[bool] = mapped_column(Boolean, default=True)

    prop: Mapped["Prop"] = relationship("Prop", back_populates="odds_snapshots")


class SbookLine(Base):
    """Current sportsbook lines used for consensus calculation."""
    __tablename__ = "sbook_lines"
    __table_args__ = (
        UniqueConstraint("player_name", "stat_type", "game_date", "sportsbook", name="uq_sbook_line"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_name: Mapped[str] = mapped_column(String(200), index=True)
    sport: Mapped[str] = mapped_column(String(20))
    sportsbook: Mapped[str] = mapped_column(String(100))
    stat_type: Mapped[str] = mapped_column(String(100))
    game_date: Mapped[Optional[str]] = mapped_column(String(30))
    line: Mapped[float] = mapped_column(Float)
    over_odds: Mapped[Optional[float]] = mapped_column(Float)
    under_odds: Mapped[Optional[float]] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    event_id: Mapped[Optional[str]] = mapped_column(String(200))
