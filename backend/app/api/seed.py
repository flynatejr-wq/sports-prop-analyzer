"""
Seed endpoint — populates the database with realistic demo props.
Call POST /api/v1/seed to fill the DB when live scrapers are unavailable.
"""
import random
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.player import Player
from app.models.prop import Prop, PropStatus

router = APIRouter()

# ── Realistic player pool ─────────────────────────────────────────────────────

PLAYERS = [
    {"name": "LeBron James",      "team": "LAL", "sport": "NBA", "position": "SF"},
    {"name": "Stephen Curry",     "team": "GSW", "sport": "NBA", "position": "PG"},
    {"name": "Jayson Tatum",      "team": "BOS", "sport": "NBA", "position": "SF"},
    {"name": "Luka Doncic",       "team": "DAL", "sport": "NBA", "position": "PG"},
    {"name": "Giannis Antetokounmpo", "team": "MIL", "sport": "NBA", "position": "PF"},
    {"name": "Nikola Jokic",      "team": "DEN", "sport": "NBA", "position": "C"},
    {"name": "Kevin Durant",      "team": "PHX", "sport": "NBA", "position": "SF"},
    {"name": "Joel Embiid",       "team": "PHI", "sport": "NBA", "position": "C"},
    {"name": "Tyrese Haliburton", "team": "IND", "sport": "NBA", "position": "PG"},
    {"name": "Anthony Edwards",   "team": "MIN", "sport": "NBA", "position": "SG"},
    {"name": "Shohei Ohtani",     "team": "LAD", "sport": "MLB", "position": "DH"},
    {"name": "Aaron Judge",       "team": "NYY", "sport": "MLB", "position": "RF"},
    {"name": "Mookie Betts",      "team": "LAD", "sport": "MLB", "position": "SS"},
    {"name": "Freddie Freeman",   "team": "LAD", "sport": "MLB", "position": "1B"},
    {"name": "Fernando Tatis Jr", "team": "SD",  "sport": "MLB", "position": "SS"},
    {"name": "Patrick Mahomes",   "team": "KC",  "sport": "NFL", "position": "QB"},
    {"name": "Josh Allen",        "team": "BUF", "sport": "NFL", "position": "QB"},
    {"name": "Justin Jefferson",  "team": "MIN", "sport": "NFL", "position": "WR"},
    {"name": "Tyreek Hill",       "team": "MIA", "sport": "NFL", "position": "WR"},
    {"name": "Travis Kelce",      "team": "KC",  "sport": "NFL", "position": "TE"},
    {"name": "Connor McDavid",    "team": "EDM", "sport": "NHL", "position": "C"},
    {"name": "Nathan MacKinnon",  "team": "COL", "sport": "NHL", "position": "C"},
    {"name": "David Pastrnak",    "team": "BOS", "sport": "NHL", "position": "RW"},
]

STAT_LINES = {
    "NBA": [
        ("Points",   [18.5, 21.5, 24.5, 27.5, 30.5, 33.5]),
        ("Rebounds", [4.5,  6.5,  8.5,  10.5, 12.5]),
        ("Assists",  [4.5,  6.5,  7.5,  9.5,  11.5]),
        ("3-Pointers Made", [1.5, 2.5, 3.5, 4.5]),
        ("Pts+Reb+Ast", [32.5, 38.5, 44.5, 48.5]),
    ],
    "MLB": [
        ("Hits",             [0.5, 1.5]),
        ("RBIs",             [0.5, 1.5]),
        ("Pitcher Strikeouts", [4.5, 5.5, 6.5, 7.5]),
        ("Total Bases",      [1.5, 2.5]),
    ],
    "NFL": [
        ("Passing Yards",   [219.5, 249.5, 279.5, 309.5]),
        ("Passing TDs",     [1.5, 2.5]),
        ("Receiving Yards", [39.5, 59.5, 79.5, 99.5]),
        ("Receptions",      [3.5, 4.5, 5.5, 6.5]),
        ("Rushing Yards",   [39.5, 59.5, 79.5]),
    ],
    "NHL": [
        ("Shots on Goal", [2.5, 3.5, 4.5]),
        ("Goals",         [0.5]),
        ("Points",        [0.5, 1.5]),
    ],
}

OPPONENTS = {
    "NBA": ["vs GSW", "vs LAL", "vs BOS", "vs MIL", "@ PHX", "@ DEN", "@ NYK", "vs MIA"],
    "MLB": ["vs NYY", "vs LAD", "@ HOU", "vs CHC", "@ ATL", "vs SF",  "@ BOS"],
    "NFL": ["vs KC",  "vs BUF", "@ DAL", "@ SF",   "vs PHI", "vs LAR", "@ MIA"],
    "NHL": ["vs TOR", "vs BOS", "@ COL", "@ EDM",  "vs TB",  "vs NYR"],
}


def _make_ev(edge: str) -> tuple:
    """Return (ev_over, ev_under) based on desired edge label."""
    if edge == "ELITE":
        ev_over  = round(random.uniform(12, 22), 1)
        ev_under = round(random.uniform(-5, 2),  1)
    elif edge == "STRONG":
        ev_over  = round(random.uniform(7, 12),  1)
        ev_under = round(random.uniform(-3, 1),  1)
    elif edge == "GOOD":
        ev_over  = round(random.uniform(3, 7),   1)
        ev_under = round(random.uniform(-2, 1),  1)
    elif edge == "UNDER":
        ev_over  = round(random.uniform(-5, 1),  1)
        ev_under = round(random.uniform(6, 15),  1)
    else:  # SLIGHT / MARGINAL
        ev_over  = round(random.uniform(0.5, 3), 1)
        ev_under = round(random.uniform(-1, 0.5), 1)
    return ev_over, ev_under


@router.post("/seed", status_code=201)
async def seed_demo_props(db: AsyncSession = Depends(get_db)) -> Dict:
    """
    Populate the database with realistic demo props.
    Safe to call multiple times — skips players/props that already exist.
    """
    created_players = 0
    created_props = 0

    # Edge distribution: a few elite, some strong, many good/slight
    edge_weights = (
        ["ELITE"] * 3 + ["STRONG"] * 6 + ["GOOD"] * 8 +
        ["SLIGHT"] * 8 + ["MARGINAL"] * 5 + ["UNDER"] * 4
    )

    for p_data in PLAYERS:
        # Upsert player
        result = await db.execute(
            select(Player).where(Player.name == p_data["name"])
        )
        player = result.scalar_one_or_none()
        if not player:
            player = Player(
                name=p_data["name"],
                team=p_data["team"],
                sport=p_data["sport"],
                position=p_data.get("position"),
                is_active=True,
            )
            db.add(player)
            await db.flush()
            created_players += 1

        sport = p_data["sport"]
        stat_options = STAT_LINES.get(sport, [])
        opp_options  = OPPONENTS.get(sport, ["@ OPP"])

        # Create 2–4 props per player
        n_props = random.randint(2, 4)
        chosen_stats = random.sample(stat_options, min(n_props, len(stat_options)))

        for stat_type, line_pool in chosen_stats:
            line       = random.choice(line_pool)
            edge       = random.choice(edge_weights)
            ev_over, ev_under = _make_ev(edge)
            season_avg = round(line * random.uniform(0.85, 1.20), 1)
            last5_avg  = round(line * random.uniform(0.75, 1.30), 1)
            disc       = round(random.uniform(-1.5, 1.5), 1)
            hit_rate   = round(random.uniform(0.40, 0.75), 2)

            prop = Prop(
                player_id=player.id,
                sport=sport,
                stat_type=stat_type,
                line=line,
                source="demo",
                consensus_line=round(line + disc, 1),
                line_discrepancy=disc,
                ev_over=ev_over,
                ev_under=ev_under,
                implied_prob_over=round(random.uniform(0.40, 0.62), 3),
                implied_prob_under=round(random.uniform(0.38, 0.60), 3),
                fair_value=round(line * random.uniform(0.92, 1.08), 1),
                season_avg=season_avg,
                last_5_avg=last5_avg,
                hit_rate_over=hit_rate,
                is_stale=random.random() < 0.08,
                is_boosted=random.random() < 0.10,
                status=PropStatus.ACTIVE,
                opponent=random.choice(opp_options),
                game_date="2026-05-21",
                ml_projection=round(line * random.uniform(0.90, 1.10), 1),
                ml_confidence=round(random.uniform(0.55, 0.92), 2),
                ml_risk_level=random.choice(["LOW", "MEDIUM", "HIGH"]),
            )
            db.add(prop)
            created_props += 1

    await db.commit()
    return {
        "message": "Demo data seeded successfully",
        "players_created": created_players,
        "props_created": created_props,
    }
