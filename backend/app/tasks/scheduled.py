"""
Background task scheduler — runs prop refresh, line movement detection,
and alert dispatch on configurable intervals.
Uses asyncio for simple single-process deployments.
For multi-worker production, replace with Celery Beat (celery_app.py).
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.prop_analyzer import PropAnalyzer
from app.services.alerts import dispatch_prop_alert
from app.utils.cache import cache

logger = logging.getLogger(__name__)

analyzer = PropAnalyzer()


async def refresh_props():
    """Full analysis refresh — runs every REFRESH_INTERVAL seconds."""
    logger.info("[scheduler] Starting prop refresh at %s", datetime.now(timezone.utc).isoformat())
    try:
        async with AsyncSessionLocal() as db:
            enriched = await analyzer.run_full_analysis(db)
            # Cache top props for fast API serving
            top_ev = sorted(
                [p for p in enriched if (p.get("ev_over") or 0) > 0],
                key=lambda x: max(x.get("ev_over", 0), x.get("ev_under", 0)),
                reverse=True,
            )[:50]
            await cache.set("top_props", top_ev, ttl=settings.REFRESH_INTERVAL * 2)
            logger.info("[scheduler] Cached %d top props", len(top_ev))
    except Exception as exc:
        logger.error("[scheduler] Refresh failed: %s", exc, exc_info=True)


async def check_alerts():
    """Scan cached props for alert conditions and dispatch notifications."""
    try:
        top_props = await cache.get("top_props") or []
        alert_count = 0
        for prop in top_props:
            best_ev = max(prop.get("ev_over", 0), prop.get("ev_under", 0))
            if best_ev >= settings.EV_ALERT_THRESHOLD:
                # Prevent duplicate alerts within same refresh window
                dedup_key = f"alerted:{prop.get('external_id', prop.get('player_name',''))}"
                already_alerted = await cache.get(dedup_key)
                if not already_alerted:
                    await dispatch_prop_alert(prop)
                    await cache.set(dedup_key, True, ttl=3600)
                    alert_count += 1
        if alert_count:
            logger.info("[scheduler] Dispatched %d alerts", alert_count)
    except Exception as exc:
        logger.error("[scheduler] Alert check failed: %s", exc)


async def start_background_tasks():
    """
    Long-running coroutine that drives all scheduled work.
    Designed to run as a background asyncio task alongside FastAPI.
    """
    logger.info("[scheduler] Background tasks starting (interval=%ds)", settings.REFRESH_INTERVAL)

    # Stagger initial run to let app finish startup
    await asyncio.sleep(5)

    iteration = 0
    while True:
        try:
            # Props refresh every cycle
            await refresh_props()

            # Alert check every cycle
            await check_alerts()

            iteration += 1
            logger.debug("[scheduler] Iteration %d complete", iteration)
        except asyncio.CancelledError:
            logger.info("[scheduler] Background tasks cancelled")
            return
        except Exception as exc:
            logger.error("[scheduler] Unexpected error: %s", exc, exc_info=True)

        await asyncio.sleep(settings.REFRESH_INTERVAL)
