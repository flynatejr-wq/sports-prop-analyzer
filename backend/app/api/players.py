"""Players API — search, profiles, analytics, and projection endpoints."""
import logging
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel

from app.database import get_db
from app.models.player import Player, PlayerStats
from app.models.prop import Prop, PropStatus, PropResult
from app.services.player_analytics import weighted_projection, recommend_vs_line
from app.utils.cache import cache

logger = logging.getLogger(__name__)
router = APIRouter()


class PlayerOut(BaseModel):
    id: int
    name: str
    sport: str
    team: Optional[str]
    position: Optional[str]
    injury_status: Optional[str]
    injury_note: Optional[str]
    image_url: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class PlayerAnalyticsOut(BaseModel):
    player_id: int
    player_name: str
    sport: str
    stat_type: str
    last_5_avg: Optional[float]
    last_10_avg: Optional[float]
    season_avg: Optional[float]
    home_avg: Optional[float]
    away_avg: Optional[float]
    trend: str
    games_played: int
    recent_games: List[Dict]


@router.get("/", response_model=List[PlayerOut])
async def search_players(
    q: Optional[str] = Query(None, description="Name search"),
    sport: Optional[str] = Query(None),
    with_active_props: bool = Query(False),
    limit: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    query = select(Player).where(Player.is_active == True)
    if q:
        query = query.where(Player.name.ilike(f"%{q}%"))
    if sport:
        query = query.where(Player.sport == sport.upper())
    if with_active_props:
        from sqlalchemy.orm import selectinload
        query = query.join(Prop, Prop.player_id == Player.id).where(Prop.status == PropStatus.ACTIVE)
    query = query.order_by(Player.name).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{player_id}", response_model=PlayerOut)
async def get_player(player_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Player).where(Player.id == player_id))
    player = result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/{player_id}/analytics", response_model=PlayerAnalyticsOut)
async def get_player_analytics(
    player_id: int,
    stat_type: str = Query("points"),
    db: AsyncSession = Depends(get_db),
):
    """Return full analytics breakdown for a player and stat type."""
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    from app.services.ev_calculator import _normal_cdf
    col = _stat_type_to_col(stat_type)

    stats_result = await db.execute(
        select(PlayerStats)
        .where(PlayerStats.player_id == player_id)
        .order_by(PlayerStats.game_date.desc())
        .limit(20)
    )
    stats = stats_result.scalars().all()

    if not stats:
        raise HTTPException(status_code=404, detail="No stats found for this player")

    def val(s: PlayerStats) -> Optional[float]:
        return getattr(s, col, None) if col else None

    values = [v for s in stats if (v := val(s)) is not None]
    home_vals = [v for s in stats if s.is_home and (v := val(s)) is not None]
    away_vals = [v for s in stats if not s.is_home and (v := val(s)) is not None]

    last_5 = values[:5]
    last_10 = values[:10]
    season_avg = sum(values) / len(values) if values else 0.0

    # Trend
    if len(last_5) >= 3 and season_avg > 0:
        last_5_avg = sum(last_5) / len(last_5)
        if last_5_avg > season_avg * 1.10:
            trend = "HOT"
        elif last_5_avg < season_avg * 0.90:
            trend = "COLD"
        else:
            trend = "NEUTRAL"
    else:
        trend = "NEUTRAL"

    recent_games = [
        {
            "game_date": s.game_date,
            "opponent": s.opponent,
            "is_home": s.is_home,
            "value": val(s),
            "minutes": s.minutes,
        }
        for s in stats[:10]
    ]

    return PlayerAnalyticsOut(
        player_id=player_id,
        player_name=player.name,
        sport=player.sport,
        stat_type=stat_type,
        last_5_avg=round(sum(last_5) / len(last_5), 2) if last_5 else None,
        last_10_avg=round(sum(last_10) / len(last_10), 2) if last_10 else None,
        season_avg=round(season_avg, 2),
        home_avg=round(sum(home_vals) / len(home_vals), 2) if home_vals else None,
        away_avg=round(sum(away_vals) / len(away_vals), 2) if away_vals else None,
        trend=trend,
        games_played=len(values),
        recent_games=recent_games,
    )


@router.get("/{player_id}/projection")
async def get_player_projection(
    player_id: int,
    stat_type: str = Query("points"),
    line: Optional[float] = Query(None),
    is_home: bool = Query(True),
    opp_def_rating: float = Query(50.0),
    db: AsyncSession = Depends(get_db),
) -> Dict:
    """
    Generate a weighted projection for a player and stat.
    Optionally pass a line to get a recommendation.
    """
    player_result = await db.execute(select(Player).where(Player.id == player_id))
    player = player_result.scalar_one_or_none()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    col = _stat_type_to_col(stat_type)
    stats_result = await db.execute(
        select(PlayerStats)
        .where(PlayerStats.player_id == player_id)
        .order_by(PlayerStats.game_date.desc())
        .limit(20)
    )
    stats = stats_result.scalars().all()

    def val(s: PlayerStats) -> Optional[float]:
        return getattr(s, col, None) if col else None

    values = [v for s in stats if (v := val(s)) is not None]
    home_vals = [v for s in stats if s.is_home and (v := val(s)) is not None]
    away_vals = [v for s in stats if not s.is_home and (v := val(s)) is not None]

    if not values:
        raise HTTPException(status_code=404, detail="Insufficient stats for projection")

    proj = weighted_projection(
        last_5=values[:5],
        last_10=values[:10],
        season_avg=sum(values) / len(values),
        home_avg=sum(home_vals) / len(home_vals) if home_vals else None,
        away_avg=sum(away_vals) / len(away_vals) if away_vals else None,
        is_home=is_home,
        opp_def_rating=opp_def_rating,
    )
    proj.player_name = player.name
    proj.stat_type = stat_type

    result = {
        "player_name": player.name,
        "stat_type": stat_type,
        "projected_value": proj.projected_value,
        "floor": proj.floor,
        "ceiling": proj.ceiling,
        "confidence": proj.confidence,
        "volatility": proj.volatility,
        "trend": proj.trend,
        "matchup_grade": proj.matchup_grade,
        "reasoning": proj.reasoning,
        "components": proj.components,
    }

    if line is not None:
        result["recommendation"] = recommend_vs_line(proj, line)
        result["line"] = line
        result["edge"] = round(proj.projected_value - line, 2)

    return result


@router.get("/{player_id}/props")
async def get_player_props(
    player_id: int,
    db: AsyncSession = Depends(get_db),
) -> List[Dict]:
    """Active props for this player with full EV data."""
    result = await db.execute(
        select(Prop)
        .where(Prop.player_id == player_id, Prop.status == PropStatus.ACTIVE)
        .order_by(desc(func.greatest(func.coalesce(Prop.ev_over, 0), func.coalesce(Prop.ev_under, 0))))
    )
    props = result.scalars().all()
    return [
        {
            "id": p.id,
            "stat_type": p.stat_type,
            "line": p.line,
            "ev_over": p.ev_over,
            "ev_under": p.ev_under,
            "consensus_line": p.consensus_line,
            "line_discrepancy": p.line_discrepancy,
            "hit_rate_over": p.hit_rate_over,
            "is_stale": p.is_stale,
        }
        for p in props
    ]


def _stat_type_to_col(stat_type: str) -> Optional[str]:
    mapping = {
        "points": "points", "pts": "points",
        "rebounds": "rebounds", "reb": "rebounds",
        "assists": "assists", "ast": "assists",
        "3-pointers made": "three_pointers", "threes": "three_pointers",
        "blocked shots": "blocks", "blocks": "blocks",
        "steals": "steals",
        "turnovers": "turnovers",
        "passing yards": "passing_yards",
        "rushing yards": "rushing_yards",
        "receiving yards": "receiving_yards",
        "receptions": "receptions",
        "hits": "hits",
        "pitcher strikeouts": "strikeouts", "strikeouts": "strikeouts",
        "shots on goal": "shots_on_goal",
        "goals": "goals",
        "saves": "saves",
    }
    return mapping.get(stat_type.lower().strip())
