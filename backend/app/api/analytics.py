"""Analytics, bankroll, and historical performance endpoints."""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, Integer, case
from pydantic import BaseModel

from app.database import get_db
from app.models.prop import Prop, PropResult, PropStatus
from app.models.player import Player
from app.models.user import UserPick, BetDirection
from app.services.kelly_criterion import (
    recommended_stake, parlay_probability, roi, clv_tracking
)

router = APIRouter()


class BankrollRequest(BaseModel):
    bankroll: float
    prob_win: float
    american_odds: float = -110.0
    fraction: float = 0.25
    max_pct: float = 0.05


class BankrollResponse(BaseModel):
    recommended_stake: float
    kelly_fraction: float
    expected_profit: float
    risk_pct: float


class PickRequest(BaseModel):
    prop_id: int
    direction: str  # over / under
    stake: float
    odds: Optional[float] = -110.0
    ev_at_pick: Optional[float] = None
    notes: Optional[str] = None


# ── Bankroll & Kelly ──────────────────────────────────────────────────────────

@router.post("/kelly", response_model=BankrollResponse)
async def kelly_sizing(req: BankrollRequest):
    """Calculate Kelly Criterion stake size."""
    from app.services.kelly_criterion import kelly_from_american, expected_profit, american_to_decimal
    from app.services.ev_calculator import american_to_decimal as atd

    kelly = kelly_from_american(req.prob_win, req.american_odds, req.fraction)
    stake = recommended_stake(req.bankroll, req.prob_win, req.american_odds, req.max_pct, req.fraction)
    decimal_odds = atd(req.american_odds)
    profit = expected_profit(stake, req.prob_win, decimal_odds)

    return BankrollResponse(
        recommended_stake=stake,
        kelly_fraction=kelly,
        expected_profit=profit,
        risk_pct=round(stake / req.bankroll * 100, 2) if req.bankroll > 0 else 0,
    )


@router.get("/summary")
async def analytics_summary(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Dashboard summary stats."""
    # Total active props
    total_active = await db.scalar(
        select(func.count()).select_from(Prop).where(Prop.status == PropStatus.ACTIVE)
    )

    # High EV count (>5%)
    high_ev = await db.scalar(
        select(func.count()).select_from(Prop).where(
            Prop.status == PropStatus.ACTIVE,
            func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0)) >= 5.0,
        )
    )

    # Stale lines
    stale = await db.scalar(
        select(func.count()).select_from(Prop).where(
            Prop.status == PropStatus.ACTIVE, Prop.is_stale == True
        )
    )

    # Pick stats
    settled_picks = await db.execute(
        select(UserPick).where(UserPick.result != PropResult.PENDING)
    )
    picks = settled_picks.scalars().all()
    wins = sum(1 for p in picks if p.result == PropResult.HIT)
    total_profit = sum(p.profit_loss or 0 for p in picks)
    total_staked = sum(p.stake for p in picks)

    return {
        "active_props": total_active or 0,
        "high_ev_props": high_ev or 0,
        "stale_lines": stale or 0,
        "picks_tracked": len(picks),
        "wins": wins,
        "losses": len(picks) - wins,
        "hit_rate": round(wins / len(picks) * 100, 1) if picks else 0.0,
        "total_profit_units": round(total_profit, 2),
        "roi_pct": roi(total_profit, total_staked),
    }


@router.get("/hit-rates")
async def hit_rates_by_stat(
    sport: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """Historical hit rates grouped by stat type for settled props."""
    query = (
        select(
            Prop.stat_type,
            func.count().label("total"),
            func.sum(case((Prop.result == PropResult.HIT, 1), else_=0)).label("hits"),
            func.avg(Prop.ev_over).label("avg_ev"),
        )
        .where(Prop.result != PropResult.PENDING)
        .group_by(Prop.stat_type)
        .order_by(func.count().desc())
    )
    if sport:
        query = query.where(Prop.sport == sport.upper())

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "stat_type": row.stat_type,
            "total": row.total,
            "hits": row.hits or 0,
            "hit_rate": round((row.hits or 0) / row.total * 100, 1),
            "avg_ev": round(float(row.avg_ev or 0), 2),
        }
        for row in rows
    ]


@router.get("/odds-movement/{prop_id}")
async def odds_movement(prop_id: int, db: AsyncSession = Depends(get_db)) -> List[Dict]:
    """Return historical odds snapshots for a prop (line movement chart data)."""
    from app.models.odds import OddsSnapshot
    result = await db.execute(
        select(OddsSnapshot)
        .where(OddsSnapshot.prop_id == prop_id)
        .order_by(OddsSnapshot.created_at.asc())
    )
    snaps = result.scalars().all()
    return [
        {
            "timestamp": s.created_at.isoformat() if s.created_at else None,
            "sportsbook": s.sportsbook,
            "line": s.line,
            "over_odds": s.over_odds,
            "under_odds": s.under_odds,
        }
        for s in snaps
    ]


# ── User Picks ─────────────────────────────────────────────────────────────────

@router.post("/picks", status_code=201)
async def add_pick(req: PickRequest, db: AsyncSession = Depends(get_db)) -> Dict:
    pick = UserPick(
        prop_id=req.prop_id,
        direction=BetDirection(req.direction.lower()),
        stake=req.stake,
        odds=req.odds,
        ev_at_pick=req.ev_at_pick,
        notes=req.notes,
    )
    db.add(pick)
    await db.flush()
    return {"id": pick.id, "message": "Pick saved"}


class SettlePickRequest(BaseModel):
    result: str           # "hit" or "miss"
    actual_value: Optional[float] = None


@router.patch("/picks/{pick_id}")
async def settle_pick(pick_id: int, req: SettlePickRequest, db: AsyncSession = Depends(get_db)) -> Dict:
    """Mark a pick as hit or miss and calculate profit/loss."""
    result = await db.execute(select(UserPick).where(UserPick.id == pick_id))
    pick = result.scalar_one_or_none()
    if not pick:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Pick not found")

    pick.result = PropResult.HIT if req.result.lower() == "hit" else PropResult.MISS

    if pick.result == PropResult.HIT:
        odds = pick.odds or -110.0
        if odds > 0:
            profit = pick.stake * (odds / 100)
        else:
            profit = pick.stake * (100 / abs(odds))
        pick.profit_loss = round(profit, 2)
    else:
        pick.profit_loss = -round(pick.stake, 2)

    return {
        "id": pick.id,
        "result": pick.result.value,
        "profit_loss": pick.profit_loss,
    }


@router.delete("/picks/{pick_id}", status_code=204)
async def delete_pick(pick_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a tracked pick."""
    result = await db.execute(select(UserPick).where(UserPick.id == pick_id))
    pick = result.scalar_one_or_none()
    if pick:
        await db.delete(pick)


@router.get("/picks")
async def get_picks(db: AsyncSession = Depends(get_db)) -> List[Dict]:
    result = await db.execute(
        select(UserPick).join(Prop, UserPick.prop_id == Prop.id, isouter=True)
        .order_by(UserPick.created_at.desc()).limit(100)
    )
    picks = result.scalars().all()
    return [
        {
            "id": p.id,
            "prop_id": p.prop_id,
            "direction": p.direction.value,
            "stake": p.stake,
            "odds": p.odds,
            "ev_at_pick": p.ev_at_pick,
            "result": p.result.value,
            "profit_loss": p.profit_loss,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in picks
    ]
