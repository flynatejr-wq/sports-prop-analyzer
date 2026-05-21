"""
PropEdge AI — FastAPI application entry point.
Starts APScheduler, mounts all routers, and applies middleware.
"""
import logging
import logging.config
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.openapi.utils import get_openapi

from app.api import analytics, props, websocket
from app.api.line_movement import router as line_movement_router
from app.api.players import router as players_router
from app.api.seed import router as seed_router
from app.api.settings_api import router as settings_router
from app.config import settings
from app.database import Base, engine
from app.middleware.logging_middleware import RequestLoggingMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.tasks.apscheduler_tasks import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting %s", settings.APP_NAME)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    await start_scheduler()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    await stop_scheduler()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="PropEdge AI",
    description=(
        "Real-time sports prop betting intelligence platform. "
        "Scans PrizePicks, WSPN, DraftKings, FanDuel, and more to find +EV props."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost first) ───────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    RateLimiterMiddleware,
    requests_per_window=120,
    window_seconds=60,
)

# ── API Routers ────────────────────────────────────────────────────────────────
V1 = "/api/v1"
app.include_router(props.router,             prefix=f"{V1}/props",         tags=["Props"])
app.include_router(analytics.router,         prefix=f"{V1}/analytics",     tags=["Analytics"])
app.include_router(players_router,           prefix=f"{V1}/players",       tags=["Players"])
app.include_router(line_movement_router,     prefix=f"{V1}/line-movement", tags=["Line Movement"])
app.include_router(settings_router,          prefix=f"{V1}/settings",      tags=["Settings"])
app.include_router(seed_router,              prefix=f"{V1}",               tags=["Seed"])
app.include_router(websocket.router,         prefix="/ws",                 tags=["WebSocket"])


# ── Health & info endpoints ────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    from app.utils.cache import cache
    last_refresh = await cache.get("last_refresh")
    return {
        "status": "healthy",
        "version": "2.0.0",
        "app": settings.APP_NAME,
        "last_data_refresh": last_refresh,
    }


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "docs": "/docs",
        "api": f"{V1}/props/top",
        "websocket": "/ws/live",
    }


# ── Custom OpenAPI schema ──────────────────────────────────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["info"]["x-logo"] = {"url": "https://propedge.ai/logo.png"}
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi
