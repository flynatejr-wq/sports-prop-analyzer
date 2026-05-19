"""
APScheduler-based task scheduler.
Replaces the simple asyncio loop with a proper job scheduler
that supports cron expressions, misfire handling, and job persistence.

Usage: imported and started in app/main.py lifespan.
"""
import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from app.config import settings
from app.database import AsyncSessionLocal
from app.utils.cache import cache

logger = logging.getLogger(__name__)

# ── Scheduler singleton ────────────────────────────────────────────────────────
_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        jobstores = {"default": MemoryJobStore()}
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {
            "coalesce": True,           # merge missed executions into one
            "max_instances": 1,         # prevent overlapping runs
            "misfire_grace_time": 30,   # allow 30s late start
        }
        _scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone="UTC",
        )
        _scheduler.add_listener(_on_job_error, EVENT_JOB_ERROR)
        _scheduler.add_listener(_on_job_executed, EVENT_JOB_EXECUTED)
    return _scheduler


def _on_job_error(event):
    logger.error("[APScheduler] Job %s failed: %s", event.job_id, event.exception)


def _on_job_executed(event):
    logger.debug("[APScheduler] Job %s executed in %.2fs", event.job_id, event.retval or 0)


# ── Job implementations ────────────────────────────────────────────────────────

async def job_refresh_props():
    """Full prop analysis refresh — runs every REFRESH_INTERVAL seconds."""
    logger.info("[job] prop_refresh starting at %s", datetime.now(timezone.utc).isoformat())
    start = datetime.now(timezone.utc)
    try:
        from app.services.prop_analyzer import PropAnalyzer
        async with AsyncSessionLocal() as db:
            enriched = await PropAnalyzer().run_full_analysis(db)
            # Cache top 50 by EV
            top = sorted(
                enriched,
                key=lambda p: max(p.get("ev_over", 0) or 0, p.get("ev_under", 0) or 0),
                reverse=True,
            )[:50]
            await cache.set("top_props", top, ttl=settings.REFRESH_INTERVAL * 2)
            await cache.set("last_refresh", datetime.now(timezone.utc).isoformat(), ttl=600)
            elapsed = (datetime.now(timezone.utc) - start).total_seconds()
            logger.info("[job] prop_refresh done: %d props in %.1fs", len(enriched), elapsed)
    except Exception as exc:
        logger.error("[job] prop_refresh failed: %s", exc, exc_info=True)


async def job_check_alerts():
    """Dispatch alerts for high-EV props."""
    try:
        from app.services.alerts import dispatch_prop_alert
        top_props = await cache.get("top_props") or []
        sent = 0
        for prop in top_props:
            best_ev = max(prop.get("ev_over", 0) or 0, prop.get("ev_under", 0) or 0)
            if best_ev < settings.EV_ALERT_THRESHOLD:
                continue
            dedup_key = f"alerted:{prop.get('external_id', prop.get('player_name', ''))}"
            if await cache.get(dedup_key):
                continue
            await dispatch_prop_alert(prop)
            await cache.set(dedup_key, True, ttl=3600)
            sent += 1
        if sent:
            logger.info("[job] alert_check: sent %d alerts", sent)
    except Exception as exc:
        logger.error("[job] alert_check failed: %s", exc)


async def job_refresh_injuries():
    """Refresh injury reports every 5 minutes."""
    try:
        from app.scrapers.injury import InjuryScraper
        scraper = InjuryScraper()
        injuries = await scraper.get_all_sports_injuries()
        # Build flat lookup
        flat = {}
        for sport, report_list in injuries.items():
            for r in report_list:
                flat[r.player_name.lower()] = {"status": r.status, "sport": sport, "note": r.note}
        await cache.set("injury_map", flat, ttl=300)
        total = sum(len(v) for v in injuries.values())
        logger.info("[job] injury_refresh: %d injuries cached", total)
    except Exception as exc:
        logger.error("[job] injury_refresh failed: %s", exc)


async def job_refresh_wspn():
    """Refresh WSPN projections every 10 minutes."""
    try:
        from app.scrapers.wspn import WSPNScraper
        scraper = WSPNScraper()
        sports = ["NBA", "NFL", "MLB", "NHL"]
        all_projections = {}
        for sport in sports:
            projections = await scraper.get_projections(sport)
            all_projections[sport] = [
                {
                    "player_name": p.player_name,
                    "stat_type": p.stat_type,
                    "projected_value": p.projected_value,
                    "confidence": p.confidence,
                    "floor": p.floor_value,
                    "ceiling": p.ceiling_value,
                }
                for p in projections
            ]
        await cache.set("wspn_projections", all_projections, ttl=600)
        logger.info("[job] wspn_refresh: %d sports refreshed", len(sports))
    except Exception as exc:
        logger.error("[job] wspn_refresh failed: %s", exc)


async def job_cleanup_old_props():
    """Mark settled/old props as inactive at midnight UTC."""
    try:
        from datetime import date, timedelta
        from sqlalchemy import update
        from app.models.prop import Prop, PropStatus
        async with AsyncSessionLocal() as db:
            yesterday = (date.today() - timedelta(days=1)).isoformat()
            await db.execute(
                update(Prop)
                .where(Prop.game_date < yesterday, Prop.status == PropStatus.ACTIVE)
                .values(status=PropStatus.SETTLED)
            )
            await db.commit()
            logger.info("[job] cleanup: settled stale props before %s", yesterday)
    except Exception as exc:
        logger.error("[job] cleanup failed: %s", exc)


async def job_retrain_models():
    """Retrain ML models using latest historical data."""
    try:
        from app.ml.model_trainer import train_ensemble
        from app.ml.feature_engineering import build_training_dataset
        from sqlalchemy import select
        from app.models.prop import Prop, PropResult

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Prop).where(Prop.result != PropResult.PENDING).limit(5000)
            )
            settled_props = result.scalars().all()

            if len(settled_props) < settings.MIN_SAMPLES_FOR_TRAINING:
                logger.info("[job] retrain: only %d samples, need %d — skipping",
                            len(settled_props), settings.MIN_SAMPLES_FOR_TRAINING)
                return

            # Build training data (simplified — full implementation joins player stats)
            historical = [
                {
                    "stat_type": p.stat_type,
                    "line": p.line,
                    "actual_value": p.actual_value,
                    "player_stats": [],  # TODO: join PlayerStats for full feature set
                    "sport": p.sport,
                }
                for p in settled_props
                if p.actual_value is not None
            ]

            X, y = build_training_dataset(historical)
            if X is None:
                return

            # Group by sport and train
            sports = list({p.sport for p in settled_props})
            for sport in sports:
                metrics = train_ensemble(X, y, sport=sport, stat_type="all")
                logger.info("[job] retrain: %s metrics=%s", sport, metrics)

        await cache.set("last_retrain", datetime.now(timezone.utc).isoformat(), ttl=86400)
    except Exception as exc:
        logger.error("[job] retrain failed: %s", exc)


# ── Scheduler setup ────────────────────────────────────────────────────────────

def configure_jobs(scheduler: AsyncIOScheduler):
    """Register all jobs with their schedules."""
    interval = settings.REFRESH_INTERVAL

    scheduler.add_job(
        job_refresh_props,
        "interval",
        seconds=interval,
        id="prop_refresh",
        name="Prop Analysis Refresh",
        next_run_time=datetime.now(timezone.utc),  # run immediately on start
    )

    scheduler.add_job(
        job_check_alerts,
        "interval",
        seconds=interval + 5,  # slight offset so alerts fire after refresh
        id="alert_check",
        name="Alert Dispatcher",
    )

    scheduler.add_job(
        job_refresh_injuries,
        "interval",
        minutes=5,
        id="injury_refresh",
        name="Injury Report Refresh",
    )

    scheduler.add_job(
        job_refresh_wspn,
        "interval",
        minutes=10,
        id="wspn_refresh",
        name="WSPN Projections Refresh",
    )

    scheduler.add_job(
        job_cleanup_old_props,
        "cron",
        hour=0,
        minute=5,
        id="prop_cleanup",
        name="Old Prop Cleanup",
    )

    scheduler.add_job(
        job_retrain_models,
        "cron",
        hour=3,
        minute=0,
        id="model_retrain",
        name="ML Model Retraining",
    )

    logger.info("[APScheduler] %d jobs registered", len(scheduler.get_jobs()))


async def start_scheduler() -> AsyncIOScheduler:
    scheduler = get_scheduler()
    configure_jobs(scheduler)
    scheduler.start()
    logger.info("[APScheduler] Scheduler started")
    return scheduler


async def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("[APScheduler] Scheduler stopped")
