"""
Props API — CRUD + analysis endpoints for props.
Includes top picks, EV ranking, filters, and per-prop detail.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.database import get_db
from app.models.player import Player
from app.models.prop import Prop, PropStatus
from app.services.prop_analyzer import PropAnalyzer
from app.utils.cache import cache

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
    source: str = "oddsapi"
    ev_over: Optional[float]
    ev_under: Optional[float]
    edge_classification: Optional[str] = None
    consensus_line: Optional[float]
    line_discrepancy: Optional[float]
    fair_value: Optional[float]
    implied_prob_over: Optional[float]
    implied_prob_under: Optional[float]
    fair_prob_over: Optional[float] = None
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
    ai_insight: Optional[str] = None

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
        "source": prop.source,
        "ev_over": prop.ev_over,
        "ev_under": prop.ev_under,
        "edge_classification": None,
        "consensus_line": prop.consensus_line,
        "line_discrepancy": prop.line_discrepancy,
        "fair_value": prop.fair_value,
        "implied_prob_over": prop.implied_prob_over,
        "implied_prob_under": prop.implied_prob_under,
        "fair_prob_over": prop.implied_prob_over,  # best proxy without separate column
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
        "ai_insight": None,
    }

    if prop.player:
        d["player_name"] = prop.player.name
        d["team"] = prop.player.team
        d["image_url"] = prop.player.image_url

    # Classify edge
    best_ev = max(d["ev_over"] or 0, d["ev_under"] or 0)
    from app.services.ev_calculator import classify_edge
    d["edge_classification"] = classify_edge(best_ev)

    # Generate AI insight text
    d["ai_insight"] = _generate_ai_insight(d)

    return d


def _generate_ai_insight(d: Dict) -> str:
    """Generate a natural-language explanation of why this prop has edge."""
    parts: List[str] = []
    ev_over = d.get("ev_over") or 0
    ev_under = d.get("ev_under") or 0
    best_ev = max(ev_over, ev_under)
    direction = "OVER" if ev_over >= ev_under else "UNDER"
    player = d.get("player_name", "Player")
    stat = d.get("stat_type", "stat")
    line = d.get("line")
    consensus = d.get("consensus_line")
    disc = d.get("line_discrepancy")
    hit_rate = d.get("hit_rate_over")
    season_avg = d.get("season_avg")
    last5 = d.get("last_5_avg")
    source = d.get("source", "oddsapi")
    prob_over = d.get("implied_prob_over") or 0.5

    # Edge explanation
    if best_ev >= 10:
        parts.append(
            f"Elite +{best_ev:.1f}% edge detected — books are significantly mispricing "
            f"{player}'s {stat.lower()} {direction} {line}."
        )
    elif best_ev >= 5:
        parts.append(
            f"Strong +{best_ev:.1f}% edge vs sportsbook consensus on "
            f"{stat.lower()} {direction} {line}."
        )
    elif best_ev > 0:
        parts.append(
            f"+{best_ev:.1f}% edge identified across sportsbook lines."
        )

    # Cross-book consensus context
    if source == "oddsapi" and consensus is not None:
        parts.append(
            f"Fair probability derived by removing vig across multiple books: "
            f"{prob_over*100:.0f}% chance of going {direction}."
        )

    # Line discrepancy
    if disc is not None and abs(disc) >= 0.5:
        if disc < 0:
            parts.append(
                f"PrizePicks line is {abs(disc):.1f} below the sportsbook consensus — "
                f"value on the OVER vs market."
            )
        else:
            parts.append(
                f"PrizePicks line sits {disc:.1f} above consensus — "
                f"value on the UNDER vs market."
            )

    # Historical hit rate
    if hit_rate is not None:
        pct = round(hit_rate * 100)
        if direction == "OVER" and pct >= 60:
            parts.append(f"Hit OVER {pct}% of last 5 games at this line.")
        elif direction == "UNDER" and pct <= 40:
            parts.append(f"Hit UNDER {100 - pct}% of last 5 games at this line.")

    # Trend vs season avg
    if season_avg and last5:
        trend = last5 - season_avg
        if abs(trend) >= 2:
            word = "above" if trend > 0 else "below"
            parts.append(
                f"Running {abs(trend):.1f} {word} season average "
                f"over last 5 games ({last5:.1f} vs {season_avg:.1f} avg)."
            )

    # Stale line signal
    if d.get("is_stale"):
        parts.append(
            "Line appears stale — consensus has moved but this book hasn't adjusted. "
            "Sharp players typically target these discrepancies."
        )

    # Fallback
    if not parts:
        parts.append(
            f"Sportsbook consensus line: {consensus or line}. "
            f"Implied over probability: {prob_over*100:.0f}%."
        )

    return " ".join(parts)


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
        .options(joinedload(Prop.player))
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
    enriched = list(await asyncio.gather(*[_enrich_with_player(db, p) for p in props]))

    await cache.set(cache_key, enriched, ttl=30)
    return enriched


@router.get("/best-bets", response_model=List[PropOut])
async def get_best_bets(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Best bets: highest EV props sorted by edge."""
    query = (
        select(Prop)
        .options(joinedload(Prop.player))
        .where(
            Prop.status == PropStatus.ACTIVE,
            or_(
                Prop.ev_over.isnot(None),
                Prop.ev_under.isnot(None),
            ),
        )
        .order_by(
            desc(func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0)))
        )
        .limit(20)
    )
    if sport:
        query = query.where(Prop.sport == sport.upper())

    result = await db.execute(query)
    return list(await asyncio.gather(*[_enrich_with_player(db, p) for p in result.scalars().all()]))


@router.get("/mispriced", response_model=List[PropOut])
async def get_mispriced_props(
    db: AsyncSession = Depends(get_db),
):
    """Props with the largest line discrepancy vs sportsbook consensus."""
    query = (
        select(Prop)
        .options(joinedload(Prop.player))
        .where(
            Prop.status == PropStatus.ACTIVE,
            Prop.line_discrepancy.isnot(None),
        )
        .order_by(desc(func.abs(Prop.line_discrepancy)))
        .limit(20)
    )
    result = await db.execute(query)
    return list(await asyncio.gather(*[_enrich_with_player(db, p) for p in result.scalars().all()]))


@router.get("/sharp-action", response_model=List[PropOut])
async def get_sharp_action(
    db: AsyncSession = Depends(get_db),
):
    """Stale or rapidly-moving lines — potential sharp money signal."""
    query = (
        select(Prop)
        .options(joinedload(Prop.player))
        .where(
            Prop.status == PropStatus.ACTIVE,
            or_(Prop.is_stale, Prop.is_boosted),
        )
        .order_by(
            desc(func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0)))
        )
        .limit(20)
    )
    result = await db.execute(query)
    return list(await asyncio.gather(*[_enrich_with_player(db, p) for p in result.scalars().all()]))


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
    from app.services.kelly_criterion import parlay_ev as calc_parlay_ev
    from app.services.kelly_criterion import parlay_probability

    # PrizePicks payout table by leg count
    PP_PAYOUTS = {2: 3.0, 3: 5.0, 4: 10.0, 5: 20.0, 6: 40.0}
    payout = PP_PAYOUTS.get(leg_count, 3.0)

    query = (
        select(Prop)
        .options(joinedload(Prop.player))
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

    probs = [leg["prob"] for leg in legs]
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
        select(Prop).options(joinedload(Prop.player)).where(Prop.id == prop_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Prop not found")
    return await _enrich_with_player(db, prop)


@router.post("/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a full prop analysis refresh."""
    from app.database import AsyncSessionLocal

    async def _run_with_own_session():
        async with AsyncSessionLocal() as db:
            await analyzer.run_full_analysis(db)

    background_tasks.add_task(_run_with_own_session)
    return {"message": "Refresh triggered", "status": "queued"}


@router.get("/search/{player_name}", response_model=List[PropOut])
async def search_player_props(
    player_name: str,
    db: AsyncSession = Depends(get_db),
):
    """Search active props for a specific player."""
    query = (
        select(Prop)
        .options(joinedload(Prop.player))
        .join(Player, Prop.player_id == Player.id)
        .where(
            Player.name.ilike(f"%{player_name}%"),
            Prop.status == PropStatus.ACTIVE,
        )
    )
    result = await db.execute(query)
    return list(await asyncio.gather(*[_enrich_with_player(db, p) for p in result.scalars().all()]))
