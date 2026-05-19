"""Player and PlayerStats ORM models."""
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import Optional, List


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    sport: Mapped[str] = mapped_column(String(20), index=True)   # NBA, NFL, MLB, NHL, NCAAB
    team: Mapped[Optional[str]] = mapped_column(String(100))
    team_abbr: Mapped[Optional[str]] = mapped_column(String(10))
    position: Mapped[Optional[str]] = mapped_column(String(20))
    image_url: Mapped[Optional[str]] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    injury_status: Mapped[Optional[str]] = mapped_column(String(50))  # OUT, GTD, QUESTIONABLE, etc.
    injury_note: Mapped[Optional[str]] = mapped_column(String(500))

    stats: Mapped[List["PlayerStats"]] = relationship("PlayerStats", back_populates="player", cascade="all, delete-orphan")
    props: Mapped[List["Prop"]] = relationship("Prop", back_populates="player")


class PlayerStats(Base):
    __tablename__ = "player_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "game_date", "season", name="uq_player_game"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id", ondelete="CASCADE"), index=True)
    season: Mapped[str] = mapped_column(String(10))
    game_date: Mapped[str] = mapped_column(String(20))
    opponent: Mapped[Optional[str]] = mapped_column(String(100))
    is_home: Mapped[Optional[bool]] = mapped_column(Boolean)

    # Universal stats
    minutes: Mapped[Optional[float]] = mapped_column(Float)
    points: Mapped[Optional[float]] = mapped_column(Float)
    assists: Mapped[Optional[float]] = mapped_column(Float)
    rebounds: Mapped[Optional[float]] = mapped_column(Float)
    steals: Mapped[Optional[float]] = mapped_column(Float)
    blocks: Mapped[Optional[float]] = mapped_column(Float)
    turnovers: Mapped[Optional[float]] = mapped_column(Float)
    three_pointers: Mapped[Optional[float]] = mapped_column(Float)

    # NFL
    passing_yards: Mapped[Optional[float]] = mapped_column(Float)
    passing_tds: Mapped[Optional[float]] = mapped_column(Float)
    rushing_yards: Mapped[Optional[float]] = mapped_column(Float)
    receiving_yards: Mapped[Optional[float]] = mapped_column(Float)
    receptions: Mapped[Optional[float]] = mapped_column(Float)

    # MLB
    hits: Mapped[Optional[float]] = mapped_column(Float)
    strikeouts: Mapped[Optional[float]] = mapped_column(Float)
    earned_runs: Mapped[Optional[float]] = mapped_column(Float)
    home_runs: Mapped[Optional[float]] = mapped_column(Float)
    rbi: Mapped[Optional[float]] = mapped_column(Float)

    # NHL
    goals: Mapped[Optional[float]] = mapped_column(Float)
    shots_on_goal: Mapped[Optional[float]] = mapped_column(Float)
    saves: Mapped[Optional[float]] = mapped_column(Float)

    # Context
    team_pace: Mapped[Optional[float]] = mapped_column(Float)
    usage_rate: Mapped[Optional[float]] = mapped_column(Float)
    opp_def_rating: Mapped[Optional[float]] = mapped_column(Float)

    player: Mapped["Player"] = relationship("Player", back_populates="stats")
