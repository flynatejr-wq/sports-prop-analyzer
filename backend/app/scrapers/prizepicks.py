"""
PrizePicks scraper — uses the public (unofficial) REST API.
Endpoints discovered via browser network inspection.
No auth required for read-only projections access.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import settings
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# PrizePicks stat_type id → human readable name
STAT_TYPE_MAP: Dict[str, str] = {
    "points": "Points",
    "rebounds": "Rebounds",
    "assists": "Assists",
    "pts_rebs_asts": "Pts+Reb+Ast",
    "pts_rebs": "Pts+Reb",
    "pts_asts": "Pts+Ast",
    "rebs_asts": "Reb+Ast",
    "3-pt_made": "3-Pointers Made",
    "blocked_shots": "Blocked Shots",
    "steals": "Steals",
    "turnovers": "Turnovers",
    "fantasy_score": "Fantasy Score",
    "passing_yards": "Passing Yards",
    "passing_touchdowns": "Passing TDs",
    "rushing_yards": "Rushing Yards",
    "receiving_yards": "Receiving Yards",
    "receptions": "Receptions",
    "hits": "Hits",
    "runs_batted_in": "RBIs",
    "pitcher_strikeouts": "Pitcher Strikeouts",
    "shots_on_goal": "Shots on Goal",
    "goals": "Goals",
    "saves": "Saves",
}

SPORT_LEAGUE_MAP = {
    "NBA": "NBA",
    "NFL": "NFL",
    "MLB": "MLB",
    "NHL": "NHL",
    "NCAAB": "NCAAB",
    "NCAAF": "NCAAF",
    "WNBA": "WNBA",
    "CFB": "NCAAF",
    "CBB": "NCAAB",
}


@dataclass
class PrizePicksProjection:
    player_id: str
    player_name: str
    team: str
    sport: str
    league: str
    position: Optional[str]
    image_url: Optional[str]
    stat_type: str
    line: float
    is_boosted: bool
    game_id: Optional[str]
    start_time: Optional[str]
    opponent: Optional[str]
    projection_id: str


class PrizePicksScraper(BaseScraper):
    def __init__(self):
        super().__init__(settings.PRIZEPICKS_API_BASE, "PrizePicks")
        self._pp_headers = {
            "Accept": "application/json",
            "Origin": "https://app.prizepicks.com",
            "Referer": "https://app.prizepicks.com/",
        }

    async def get_projections(
        self,
        league: Optional[str] = None,
        single_stat: bool = True,
    ) -> List[PrizePicksProjection]:
        """
        Fetch all active projections from PrizePicks.
        league: optional filter e.g. 'NBA', 'NFL'
        single_stat: when True only fetch non-combo props (cleaner for analysis)
        """
        url = f"{self.base_url}/projections"
        params: Dict[str, Any] = {
            "per_page": 250,
            "state_abbrev": "CO",   # any state — used to filter active lines
            "is_live": "false",
        }
        if league:
            params["league_id"] = await self._get_league_id(league)

        try:
            data = await self.get(url, params=params, headers=self._pp_headers)
        except Exception as exc:
            logger.error("PrizePicks projections fetch failed: %s", exc)
            return []

        return self._parse_projections(data, single_stat=single_stat)

    async def _get_league_id(self, league_name: str) -> Optional[int]:
        """Resolve league name to PrizePicks numeric league_id."""
        try:
            data = await self.get(f"{self.base_url}/leagues", headers=self._pp_headers)
            for item in data.get("data", []):
                if item.get("attributes", {}).get("name", "").upper() == league_name.upper():
                    return int(item["id"])
        except Exception:
            pass
        return None

    def _parse_projections(self, data: Dict, single_stat: bool) -> List[PrizePicksProjection]:
        projections: List[PrizePicksProjection] = []

        # Build lookup maps from included resources
        players_map: Dict[str, Dict] = {}
        stat_types_map: Dict[str, str] = {}
        leagues_map: Dict[str, str] = {}
        games_map: Dict[str, Dict] = {}

        for item in data.get("included", []):
            item_type = item.get("type", "")
            item_id = item.get("id", "")
            attrs = item.get("attributes", {})

            if item_type == "new_player":
                players_map[item_id] = attrs
            elif item_type == "stat_type":
                stat_types_map[item_id] = attrs.get("name", item_id)
            elif item_type == "league":
                leagues_map[item_id] = attrs.get("name", "")
            elif item_type == "game":
                games_map[item_id] = attrs

        for item in data.get("data", []):
            if item.get("type") != "projection":
                continue

            attrs = item.get("attributes", {})
            rels = item.get("relationships", {})

            # Skip combo props if requested
            if single_stat and attrs.get("combo_stat", False):
                continue

            # Skip suspended / inactive
            if attrs.get("status") not in (None, "normal", "pre_game"):
                continue

            player_id = (
                rels.get("new_player", {}).get("data", {}).get("id", "") or
                rels.get("player", {}).get("data", {}).get("id", "")
            )
            player = players_map.get(player_id, {})

            stat_type_id = rels.get("stat_type", {}).get("data", {}).get("id", "")
            stat_name = stat_types_map.get(stat_type_id, attrs.get("stat_type", "unknown"))

            league_id = rels.get("league", {}).get("data", {}).get("id", "")
            league_name = leagues_map.get(league_id, "")
            sport = SPORT_LEAGUE_MAP.get(league_name.upper(), league_name)

            game_id = rels.get("game", {}).get("data", {}).get("id")
            game = games_map.get(game_id, {}) if game_id else {}
            opponent = None
            if game:
                home = game.get("home_team_display_name", "")
                away = game.get("away_team_display_name", "")
                player_team = player.get("team", "")
                if player_team:
                    opponent = away if player_team in home else home

            line_score = attrs.get("line_score")
            if line_score is None:
                continue

            projections.append(
                PrizePicksProjection(
                    player_id=player_id,
                    player_name=player.get("display_name", player.get("name", "Unknown")),
                    team=player.get("team", ""),
                    sport=sport,
                    league=league_name,
                    position=player.get("position"),
                    image_url=player.get("image_url"),
                    stat_type=stat_name,
                    line=float(line_score),
                    is_boosted=attrs.get("is_promo", False),
                    game_id=game_id,
                    start_time=attrs.get("start_time"),
                    opponent=opponent,
                    projection_id=item["id"],
                )
            )

        logger.info("PrizePicks: parsed %d projections", len(projections))
        return projections

    async def get_all_sports(self) -> List[PrizePicksProjection]:
        """Fetch projections for all major sports at once."""
        return await self.get_projections(league=None, single_stat=True)
