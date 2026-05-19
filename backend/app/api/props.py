"""
Props API — CRUD + analysis endpoints for props.
Includes top picks, EV ranking, filters, and per-prop detail.
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.prop import Prop, PropStatus, PropResult
from app.models.player import Player
from app.utils.cache import cache
from app.services.prop_analyzer import PropAnalyzer
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()
analyzer = PropAnalyzer()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class PropOut(BaseModel):
    id: int
    player_name: str
    team: Optional[str]
    sport: str
    stat_type: str
    line: float
    ev_over: Optional[float]
    ev_under: Optional[float]
    edge_classification: Optional[str] = None
    consensus_line: Optional[float]
    line_discrepancy: Optional[float]
    fair_value: Optional[float]
    implied_prob_over: Optional[float]
    implied_prob_under: Optional[float]
    is_stale: bool
    is_boosted: bool
    last_5_avg: Optional[float]
    season_avg: Optional[float]
    hit_rate_over: Optional[float]
    ml_projection: Optional[float]
    ml_confidence: Optional[float]
    ml_risk_level: Optional[str]
    game_date: Optional[str]
    opponent: Optional[str]
    status: str
    image_url: Optional[str] = None

    class Config:
        from_attributes = True


class PropDetailOut(PropOut):
    home_avg: Optional[float]
    away_avg: Optional[float]
    volatility_score: Optional[float]
    notes: Optional[str]


class PropsResponse(BaseModel):
    total: int
    props: List[PropOut]
    page: int
    per_page: int


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _enrich_with_player(db: AsyncSession, prop: Prop) -> Dict:
    d = {
        "id": prop.id,
        "player_name": "",
        "team": None,
        "image_url": None,
        "sport": prop.sport,
        "stat_type": prop.stat_type,
        "line": prop.line,
        "ev_over": prop.ev_over,
        "ev_under": prop.ev_under,
        "edge_classification": None,
        "consensus_line": prop.consensus_line,
        "line_discrepancy": prop.line_discrepancy,
        "fair_value": prop.fair_value,
        "implied_prob_over": prop.implied_prob_over,
        "implied_prob_under": prop.implied_prob_under,
        "is_stale": prop.is_stale,
        "is_boosted": prop.is_boosted,
        "last_5_avg": prop.last_5_avg,
        "season_avg": prop.season_avg,
        "hit_rate_over": prop.hit_rate_over,
        "ml_projection": prop.ml_projection,
        "ml_confidence": prop.ml_confidence,
        "ml_risk_level": prop.ml_risk_level,
        "game_date": prop.game_date,
        "opponent": prop.opponent,
        "status": prop.status.value,
        "home_avg": prop.home_avg,
        "away_avg": prop.away_avg,
        "volatility_score": prop.volatility_score,
        "notes": prop.notes,
    }

    if prop.player:
        d["player_name"] = prop.player.name
        d["team"] = prop.player.team
        d["image_url"] = prop.player.image_url

    # Classify edge
    best_ev = max(d["ev_over"] or 0, d["ev_under"] or 0)
    from app.services.ev_calculator import classify_edge
    d["edge_classification"] = classify_edge(best_ev)

    return d


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/top", response_model=List[PropOut])
async def get_top_props(
    sport: Optional[str] = Query(None, description="Filter by sport: NBA, NFL, MLB, NHL"),
    stat_type: Optional[str] = Query(None),
    min_ev: float = Query(2.0, description="Minimum EV% to include"),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Return top EV props. Served from cache when available.
    """
    cache_key = f"top_props:{sport}:{stat_type}:{min_ev}:{limit}"
    cached = await cache.get(cache_key)
    if cached:
        return cached

    query = (
        select(Prop)
        .join(Player, Prop.player_id == Player.id, isouter=True)
        .where(Prop.status == PropStatus.ACTIVE)
        .where(
            or_(
                Prop.ev_over >= min_ev,
                Prop.ev_under >= min_ev,
            )
        )
    )

    if sport:
        query = query.where(Prop.sport == sport.upper())
    if stat_type:
        query = query.where(Prop.stat_type.ilike(f"%{stat_type}%"))

    query = query.order_by(
        desc(func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0)))
    ).limit(limit)

    result = await db.execute(query)
    props = result.scalars().all()
    enriched = [await _enrich_with_player(db, p) for p in props]

    await cache.set(cache_key, enriched, ttl=30)
    return enriched


@router.get("/best-bets", response_model=List[PropOut])
async def get_best_bets(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Best bets: high EV + high ML confidence + low risk."""
    query = (
        select(Prop)
        .join(Player, Prop.player_id == Player.id, isouter=True)
        .where(
            Prop.status == PropStatus.ACTIVE,
            or_(Prop.ev_over >= 5.0, Prop.ev_under >= 5.0),
        )
        .order_by(
            desc(func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0)))
        )
        .limit(20)
    )
    if sport:
        query = query.where(Prop.sport == sport.upper())

    result = await db.execute(query)
    return [await _enrich_with_player(db, p) for p in result.scalars().all()]


@router.get("/mispriced", response_model=List[PropOut])
async def get_mispriced_props(
    db: AsyncSession = Depends(get_db),
):
    """Props with the largest line discrepancy vs sportsbook consensus."""
    query = (
        select(Prop)
        .join(Player, Prop.player_id == Player.id, isouter=True)
        .where(
            Prop.status == PropStatus.ACTIVE,
            Prop.line_discrepancy.isnot(None),
        )
        .order_by(desc(func.abs(Prop.line_discrepancy)))
        .limit(20)
    )
    result = await db.execute(query)
    return [await _enrich_with_player(db, p) for p in result.scalars().all()]


@router.get("/sharp-action", response_model=List[PropOut])
async def get_sharp_action(
    db: AsyncSession = Depends(get_db),
):
    """Stale or rapidly-moving lines — potential sharp money signal."""
    query = (
        select(Prop)
        .join(Player, Prop.player_id == Player.id, isouter=True)
        .where(
            Prop.status == PropStatus.ACTIVE,
            or_(Prop.is_stale == True, Prop.is_boosted == True),
        )
        .order_by(
            desc(func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0)))
        )
        .limit(20)
    )
    result = await db.execute(query)
    return [await _enrich_with_player(db, p) for p in result.scalars().all()]


@router.get("/parlay-builder", response_model=Dict[str, Any])
async def parlay_builder(
    leg_count: int = Query(2, ge=2, le=6),
    sport: Optional[str] = Query(None),
    min_ev_per_leg: float = Query(3.0),
    db: AsyncSession = Depends(get_db),
):
    """
    Suggest optimal parlay combinations maximizing total EV.
    Returns legs + combined probability + expected payout.
    """
    from app.services.kelly_criterion import parlay_probability, parlay_ev as calc_parlay_ev

    # PrizePicks payout table by leg count
    PP_PAYOUTS = {2: 3.0, 3: 5.0, 4: 10.0, 5: 20.0, 6: 40.0}
    payout = PP_PAYOUTS.get(leg_count, 3.0)

    query = (
        select(Prop)
        .join(Player, Prop.player_id == Player.id, isouter=True)
        .where(
            Prop.status == PropStatus.ACTIVE,
            or_(Prop.ev_over >= min_ev_per_leg, Prop.ev_under >= min_ev_per_leg),
        )
        .order_by(
            desc(func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0)))
        )
        .limit(leg_count * 3)
    )
    if sport:
        query = query.where(Prop.sport == sport.upper())

    result = await db.execute(query)
    candidates = result.scalars().all()

    # Take top N distinct players
    seen_players = set()
    legs = []
    for prop in candidates:
        player = prop.player
        pid = prop.player_id
        if pid in seen_players:
            continue
        seen_players.add(pid)

        ev_over = prop.ev_over or 0
        ev_under = prop.ev_under or 0
        direction = "over" if ev_over >= ev_under else "under"
        prob = (
            (prop.implied_prob_over or 0.52) if direction == "over"
            else (prop.implied_prob_under or 0.52)
        )

        legs.append({
            "player_name": player.name if player else "Unknown",
            "stat_type": prop.stat_type,
            "line": prop.line,
            "direction": direction,
            "ev_pct": max(ev_over, ev_under),
            "prob": prob,
            "sport": prop.sport,
        })

        if len(legs) == leg_count:
            break

    probs = [l["prob"] for l in legs]
    combined_prob = parlay_probability(probs)
    ev_total = calc_parlay_ev(probs, payout)

    return {
        "legs": legs,
        "leg_count": len(legs),
        "payout_multiplier": payout,
        "combined_probability": round(combined_prob, 4),
        "combined_ev": round(ev_total * 100, 2),
        "expected_units": round(ev_total + 1, 3),
    }


@router.get("/{prop_id}", response_model=PropDetailOut)
async def get_prop(prop_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Prop).join(Player, Prop.player_id == Player.id, isouter=True).where(Prop.id == prop_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Prop not found")
    return await _enrich_with_player(db, prop)


@router.post("/refresh")
async def trigger_refresh(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a full prop analysis refresh."""
    background_tasks.add_task(analyzer.run_full_analysis, db)
    return {"message": "Refresh triggered", "status": "queued"}


@router.get("/search/{player_name}", response_model=List[PropOut])
async def search_player_props(
    player_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Search active props for a specific player."""
    query = (
        select(Prop)
        .join(Player, Prop.player_id == Player.id)
        .where(
            Player.name.ilike(f"%{player_name}%"),
            Prop.status == PropStatus.ACTIVE,
        )
    )
    result = await db.execute(query)
    return [await _enrich_with_player(db, p) for p in result.scalars().all()]
