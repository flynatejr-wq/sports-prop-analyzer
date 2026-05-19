"""Central configuration — all settings read from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    APP_NAME: str = "Sports Prop Analyzer"
    DEBUG: bool = False
    SECRET_KEY: str = "changeme-in-production"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sportsprops"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/sportsprops"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL: int = 30  # seconds

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # External APIs
    THE_ODDS_API_KEY: str = ""
    BALLDONTLIE_API_KEY: str = ""
    SLEEPER_API_BASE: str = "https://api.sleeper.app/v1"
    PRIZEPICKS_API_BASE: str = "https://api.prizepicks.com"
    ESPN_API_BASE: str = "https://site.api.espn.com/apis/site/v2/sports"
    ROTOWIRE_BASE: str = "https://www.rotowire.com"

    # Alerts
    DISCORD_WEBHOOK_URL: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    ALERT_PHONE_NUMBERS: str = ""  # comma-separated

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    ALERT_EMAIL_RECIPIENTS: str = ""

    # Analysis thresholds
    EV_ALERT_THRESHOLD: float = 5.0   # % edge to trigger alert
    MIN_CONFIDENCE: float = 55.0       # model confidence %
    STALE_LINE_MINUTES: int = 30       # minutes before line is "stale"
    REFRESH_INTERVAL: int = 30         # seconds between data refreshes

    # Scraping
    REQUEST_TIMEOUT: int = 15
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.5
    USE_PROXIES: bool = False
    PROXY_LIST: str = ""  # comma-separated proxy URLs

    # ML
    MODEL_RETRAIN_HOURS: int = 24
    MIN_SAMPLES_FOR_TRAINING: int = 100

    @property
    def proxy_list(self) -> List[str]:
        if not self.PROXY_LIST:
            return []
        return [p.strip() for p in self.PROXY_LIST.split(",") if p.strip()]

    @property
    def alert_phones(self) -> List[str]:
        if not self.ALERT_PHONE_NUMBERS:
            return []
        return [p.strip() for p in self.ALERT_PHONE_NUMBERS.split(",") if p.strip()]

    @property
    def alert_emails(self) -> List[str]:
        if not self.ALERT_EMAIL_RECIPIENTS:
            return []
        return [e.strip() for e in self.ALERT_EMAIL_RECIPIENTS.split(",") if e.strip()]


settings = Settings()
