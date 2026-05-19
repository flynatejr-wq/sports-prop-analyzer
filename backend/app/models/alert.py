"""Alert model for tracking sent notifications."""
from sqlalchemy import String, Float, Integer, Boolean, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from typing import Optional
import enum


class AlertType(str, enum.Enum):
    HIGH_EV = "high_ev"
    LINE_MOVEMENT = "line_movement"
    INJURY = "injury"
    STEAM_MOVE = "steam_move"
    STALE_LINE = "stale_line"
    PROJECTION_MISMATCH = "projection_mismatch"


class AlertChannel(str, enum.Enum):
    DISCORD = "discord"
    TELEGRAM = "telegram"
    SMS = "sms"
    EMAIL = "email"


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prop_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("props.id", ondelete="SET NULL"), nullable=True)
    alert_type: Mapped[AlertType] = mapped_column(SAEnum(AlertType), index=True)
    channel: Mapped[AlertChannel] = mapped_column(SAEnum(AlertChannel))
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text)
    ev_value: Mapped[Optional[float]] = mapped_column(Float)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text)
