"""
User settings API — stores and retrieves per-user preferences.
Uses a simple JSON config backed by Redis for now;
swap for a DB table in multi-user deployments.
"""
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.utils.cache import cache
from app.config import settings

router = APIRouter()

SETTINGS_CACHE_KEY = "user_settings:default"
SETTINGS_TTL = 86400 * 30  # 30 days


class AlertSettings(BaseModel):
    discord_enabled: bool = True
    telegram_enabled: bool = False
    sms_enabled: bool = False
    email_enabled: bool = False
    min_ev_threshold: float = Field(5.0, ge=0.0, le=50.0)
    alert_on_injury: bool = True
    alert_on_steam: bool = True
    alert_on_stale_line: bool = False


class BankrollSettings(BaseModel):
    bankroll: float = Field(1000.0, ge=0.0)
    unit_size: float = Field(10.0, ge=0.0)
    kelly_fraction: float = Field(0.25, ge=0.0, le=1.0)
    max_bet_pct: float = Field(5.0, ge=0.1, le=20.0)
    risk_tolerance: str = "MEDIUM"  # LOW, MEDIUM, HIGH


class DisplaySettings(BaseModel):
    default_sport: str = "NBA"
    default_min_ev: float = 2.0
    show_ml_predictions: bool = True
    show_stale_only: bool = False
    show_boosted: bool = False
    table_view: bool = False
    items_per_page: int = 25


class UserSettings(BaseModel):
    alerts: AlertSettings = Field(default_factory=AlertSettings)
    bankroll: BankrollSettings = Field(default_factory=BankrollSettings)
    display: DisplaySettings = Field(default_factory=DisplaySettings)
    sports_filter: list = Field(default_factory=lambda: ["NBA", "NFL", "MLB", "NHL"])
    webhook_url: Optional[str] = None
    telegram_chat_id: Optional[str] = None


DEFAULT_SETTINGS = UserSettings()


@router.get("/", response_model=UserSettings)
async def get_settings():
    """Return current user settings."""
    cached = await cache.get(SETTINGS_CACHE_KEY)
    if cached:
        try:
            return UserSettings(**cached)
        except Exception:
            pass
    return DEFAULT_SETTINGS


@router.put("/", response_model=UserSettings)
async def update_settings(new_settings: UserSettings):
    """Replace full settings object."""
    await cache.set(SETTINGS_CACHE_KEY, new_settings.model_dump(), ttl=SETTINGS_TTL)
    return new_settings


@router.patch("/alerts", response_model=AlertSettings)
async def update_alert_settings(updates: AlertSettings):
    """Update alert-specific settings only."""
    current = await get_settings()
    merged = current.model_copy(update={"alerts": updates})
    await cache.set(SETTINGS_CACHE_KEY, merged.model_dump(), ttl=SETTINGS_TTL)
    return updates


@router.patch("/bankroll", response_model=BankrollSettings)
async def update_bankroll_settings(updates: BankrollSettings):
    current = await get_settings()
    merged = current.model_copy(update={"bankroll": updates})
    await cache.set(SETTINGS_CACHE_KEY, merged.model_dump(), ttl=SETTINGS_TTL)
    return updates


@router.get("/test-discord")
async def test_discord_alert():
    """Fire a test Discord alert to verify webhook configuration."""
    from app.services.alerts import send_discord
    from app.models.alert import AlertType
    success = await send_discord(
        title="🎯 PropEdge AI — Test Alert",
        message="Your Discord alerts are configured correctly! High-EV props will appear here.",
        alert_type=AlertType.HIGH_EV,
    )
    return {"success": success, "message": "Discord test sent" if success else "Discord not configured"}


@router.get("/test-telegram")
async def test_telegram_alert():
    from app.services.alerts import send_telegram
    success = await send_telegram(
        "🎯 *PropEdge AI — Test Alert*\nYour Telegram alerts are configured correctly!"
    )
    return {"success": success}


@router.get("/system-status")
async def get_system_status():
    """Return system health and configuration status."""
    from app.utils.cache import cache as _cache
    last_refresh = await _cache.get("last_refresh")
    last_retrain = await _cache.get("last_retrain")
    top_props = await _cache.get("top_props") or []

    return {
        "status": "healthy",
        "last_refresh": last_refresh,
        "last_model_retrain": last_retrain,
        "active_props_cached": len(top_props),
        "discord_configured": bool(settings.DISCORD_WEBHOOK_URL),
        "telegram_configured": bool(settings.TELEGRAM_BOT_TOKEN),
        "sms_configured": bool(settings.TWILIO_ACCOUNT_SID),
        "odds_api_configured": bool(settings.THE_ODDS_API_KEY),
        "refresh_interval_seconds": settings.REFRESH_INTERVAL,
        "ev_alert_threshold": settings.EV_ALERT_THRESHOLD,
    }
