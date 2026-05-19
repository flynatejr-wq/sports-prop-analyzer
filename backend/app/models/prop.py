"""Prop and PropResult models — core of the analysis pipeline."""
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import Optional
import enum


class PropStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class PropResult(str, enum.Enum):
    HIT = "hit"
    MISS = "miss"
    PUSH = "push"
    PENDING = "pending"


class Prop(Base):
    __tablename__ = "props"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), index=True)

    # Source
    source: Mapped[str] = mapped_column(String(50))          # prizepicks, draftkings, fanduel, etc.
    external_id: Mapped[Optional[str]] = mapped_column(String(200), index=True)
    sport: Mapped[str] = mapped_column(String(20), index=True)
    league: Mapped[Optional[str]] = mapped_column(String(20))
    game_date: Mapped[Optional[str]] = mapped_column(String(30), index=True)
    opponent: Mapped[Optional[str]] = mapped_column(String(100))
    is_home: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Prop definition
    stat_type: Mapped[str] = mapped_column(String(100), index=True)  # "points", "rebounds", etc.
    line: Mapped[float] = mapped_column(Float)
    over_odds: Mapped[Optional[float]] = mapped_column(Float)         # American odds
    under_odds: Mapped[Optional[float]] = mapped_column(Float)

    # Status
    status: Mapped[PropStatus] = mapped_column(SAEnum(PropStatus), default=PropStatus.ACTIVE, index=True)

    # EV Analysis (populated by analysis engine)
    ev_over: Mapped[Optional[float]] = mapped_column(Float)           # % edge on over
    ev_under: Mapped[Optional[float]] = mapped_column(Float)
    consensus_line: Mapped[Optional[float]] = mapped_column(Float)    # avg across sbooks
    fair_value: Mapped[Optional[float]] = mapped_column(Float)
    implied_prob_over: Mapped[Optional[float]] = mapped_column(Float)
    implied_prob_under: Mapped[Optional[float]] = mapped_column(Float)
    line_discrepancy: Mapped[Optional[float]] = mapped_column(Float)  # PP line - consensus
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    is_boosted: Mapped[bool] = mapped_column(Boolean, default=False)

    # ML predictions
    ml_projection: Mapped[Optional[float]] = mapped_column(Float)
    ml_confidence: Mapped[Optional[float]] = mapped_column(Float)
    ml_risk_level: Mapped[Optional[str]] = mapped_column(String(20))  # LOW, MEDIUM, HIGH
    volatility_score: Mapped[Optional[float]] = mapped_column(Float)

    # Context
    last_5_avg: Mapped[Optional[float]] = mapped_column(Float)
    season_avg: Mapped[Optional[float]] = mapped_column(Float)
    home_avg: Mapped[Optional[float]] = mapped_column(Float)
    away_avg: Mapped[Optional[float]] = mapped_column(Float)
    vs_opp_avg: Mapped[Optional[float]] = mapped_column(Float)
    hit_rate_over: Mapped[Optional[float]] = mapped_column(Float)     # % of games over line

    # Outcome
    actual_value: Mapped[Optional[float]] = mapped_column(Float)
    result: Mapped[PropResult] = mapped_column(SAEnum(PropResult), default=PropResult.PENDING, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    player: Mapped["Player"] = relationship("Player", back_populates="props")
    odds_snapshots: Mapped[list["OddsSnapshot"]] = relationship("OddsSnapshot", back_populates="prop", cascade="all, delete-orphan")
    user_picks: Mapped[list["UserPick"]] = relationship("UserPick", back_populates="prop")
