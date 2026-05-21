"""
Line movement API — tracks and exposes historical line changes
for detecting sharp action and steam moves.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.odds import OddsSnapshot
from app.models.player import Player
from app.models.prop import Prop, PropStatus
from app.utils.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter()


class LineMovementEvent(BaseModel):
    prop_id: int
    player_name: str
    stat_type: str
    sport: str
    line: float
    pp_line: float
    discrepancy: float
    movement_direction: str       # "UP", "DOWN", "STABLE"
    movement_magnitude: float
    is_steam: bool
    books_moving: List[str]
    timestamp: str


class LineMovementSummary(BaseModel):
    prop_id: int
    player_name: str
    stat_type: str
    sport: str
    pp_line: float
    opening_consensus: Optional[float]
    current_consensus: Optional[float]
    total_movement: float
    movement_direction: str
    is_steam_move: bool
    snapshots: List[Dict]
    last_updated: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/recent", response_model=List[LineMovementEvent])
async def get_recent_movements(
    hours: int = Query(4, ge=1, le=48),
    sport: Optional[str] = Query(None),
    min_movement: float = Query(0.5, description="Minimum line movement to include"),
    db: AsyncSession = Depends(get_db),
):
    """
    Return props with meaningful line movement in the last N hours.
    Useful for detecting steam moves and sharp action.
    """
    cache_key = f"line_movements:{hours}:{sport}:{min_movement}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Get props with multiple snapshots
    snap_query = (
        select(
            OddsSnapshot.prop_id,
            func.min(OddsSnapshot.line).label("min_line"),
            func.max(OddsSnapshot.line).label("max_line"),
            func.count().label("snapshot_count"),
            func.array_agg(OddsSnapshot.sportsbook).label("books"),
        )
        .where(OddsSnapshot.created_at >= since)
        .group_by(OddsSnapshot.prop_id)
        .having(func.count() >= 2)
    )
    snap_result = await db.execute(snap_query)
    snapshots = snap_result.all()

    events: List[Dict] = []
    for row in snapshots:
        movement = abs(row.max_line - row.min_line)
        if movement < min_movement:
            continue

        # Get prop + player details
        prop_result = await db.execute(
            select(Prop, Player)
            .join(Player, Prop.player_id == Player.id, isouter=True)
            .where(Prop.id == row.prop_id)
        )
        prop_player = prop_result.first()
        if not prop_player:
            continue
        prop, player = prop_player

        if sport and prop.sport != sport.upper():
            continue

        # Most recent snapshot vs oldest
        snaps_result = await db.execute(
            select(OddsSnapshot)
            .where(
                OddsSnapshot.prop_id == row.prop_id,
                OddsSnapshot.created_at >= since,
            )
            .order_by(OddsSnapshot.created_at.asc())
        )
        all_snaps = snaps_result.scalars().all()
        if len(all_snaps) < 2:
            continue

        first_line = all_snaps[0].line
        last_line = all_snaps[-1].line
        net_movement = last_line - first_line

        direction = "UP" if net_movement > 0.1 else ("DOWN" if net_movement < -0.1 else "STABLE")
        is_steam = abs(net_movement) >= 1.0 and len(all_snaps) >= 3
        books = list(set(row.books or []))

        events.append({
            "prop_id": prop.id,
            "player_name": player.name if player else "Unknown",
            "stat_type": prop.stat_type,
            "sport": prop.sport,
            "line": last_line,
            "pp_line": prop.line,
            "discrepancy": round(prop.line - last_line, 2),
            "movement_direction": direction,
            "movement_magnitude": round(movement, 2),
            "is_steam": is_steam,
            "books_moving": books[:5],
            "timestamp": all_snaps[-1].created_at.isoformat() if all_snaps[-1].created_at else "",
        })

    events.sort(key=lambda e: e["movement_magnitude"], reverse=True)
    await cache.set(cache_key, events[:50], ttl=30)
    return events[:50]


@router.get("/steam-moves", response_model=List[LineMovementEvent])
async def get_steam_moves(
    db: AsyncSession = Depends(get_db),
):
    """
    Steam moves only: rapid multi-book line movement of ≥1 unit.
    Classic sharp-money signal.
    """
    return await get_recent_movements(hours=2, min_movement=1.0, db=db)


@router.get("/prop/{prop_id}", response_model=LineMovementSummary)
async def get_prop_movement(
    prop_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Full movement history for a single prop."""
    prop_result = await db.execute(
        select(Prop, Player)
        .join(Player, Prop.player_id == Player.id, isouter=True)
        .where(Prop.id == prop_id)
    )
    row = prop_result.first()
    if not row:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Prop not found")

    prop, player = row

    snaps_result = await db.execute(
        select(OddsSnapshot)
        .where(OddsSnapshot.prop_id == prop_id)
        .order_by(OddsSnapshot.created_at.asc())
    )
    snaps = snaps_result.scalars().all()

    opening = snaps[0].line if snaps else None
    current = snaps[-1].line if snaps else None
    total_movement = round(abs((current or 0) - (opening or 0)), 2)
    direction = (
        "UP" if (current or 0) > (opening or 0) + 0.1
        else "DOWN" if (current or 0) < (opening or 0) - 0.1
        else "STABLE"
    )
    is_steam = total_movement >= 1.0 and len(snaps) >= 3

    snap_dicts = [
        {
            "timestamp": s.created_at.isoformat() if s.created_at else "",
            "sportsbook": s.sportsbook,
            "line": s.line,
            "over_odds": s.over_odds,
            "under_odds": s.under_odds,
        }
        for s in snaps
    ]

    return LineMovementSummary(
        prop_id=prop_id,
        player_name=player.name if player else "Unknown",
        stat_type=prop.stat_type,
        sport=prop.sport,
        pp_line=prop.line,
        opening_consensus=opening,
        current_consensus=current,
        total_movement=total_movement,
        movement_direction=direction,
        is_steam_move=is_steam,
        snapshots=snap_dicts,
        last_updated=snaps[-1].created_at.isoformat() if snaps and snaps[-1].created_at else "",
    )


@router.get("/heatmap")
async def get_movement_heatmap(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """
    Heatmap data: player × stat_type, colored by movement magnitude.
    Used by the frontend line movement visualization.
    """
    cache_key = f"movement_heatmap:{sport}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    query = (
        select(
            Prop.stat_type,
            Player.name.label("player_name"),
            Prop.sport,
            func.coalesce(Prop.line_discrepancy, 0).label("discrepancy"),
            Prop.ev_over,
            Prop.ev_under,
            Prop.is_stale,
        )
        .join(Player, Prop.player_id == Player.id, isouter=True)
        .where(Prop.status == PropStatus.ACTIVE)
        .order_by(func.abs(func.coalesce(Prop.line_discrepancy, 0)).desc())
        .limit(100)
    )
    if sport:
        query = query.where(Prop.sport == sport.upper())

    result = await db.execute(query)
    rows = result.all()

    heatmap = [
        {
            "player_name": r.player_name or "Unknown",
            "stat_type": r.stat_type,
            "sport": r.sport,
            "discrepancy": float(r.discrepancy or 0),
            "ev": max(float(r.ev_over or 0), float(r.ev_under or 0)),
            "is_stale": r.is_stale,
        }
        for r in rows
    ]

    await cache.set(cache_key, heatmap, ttl=60)
    return heatmap
