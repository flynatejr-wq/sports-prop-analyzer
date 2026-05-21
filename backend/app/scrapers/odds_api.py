"""
TheOddsAPI scraper — pulls player prop lines from 40+ sportsbooks.
Docs: https://the-odds-api.com/lol-odds-api/
Requires API key in THE_ODDS_API_KEY env variable.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.config import settings
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

BASE_URL = "https://api.the-odds-api.com/v4"

# Sport keys used by TheOddsAPI
SPORT_KEYS = {
    "NBA": "basketball_nba",
    "NFL": "americanfootball_nfl",
    "MLB": "baseball_mlb",
    "NHL": "icehockey_nhl",
    "NCAAB": "basketball_ncaab",
    "NCAAF": "americanfootball_ncaaf",
    "WNBA": "basketball_wnba",
}

# Market keys → human readable
PLAYER_PROP_MARKETS = {
    # NBA
    "player_points": "Points",
    "player_rebounds": "Rebounds",
    "player_assists": "Assists",
    "player_threes": "3-Pointers Made",
    "player_blocks": "Blocked Shots",
    "player_steals": "Steals",
    "player_turnovers": "Turnovers",
    "player_points_rebounds_assists": "Pts+Reb+Ast",
    "player_points_rebounds": "Pts+Reb",
    "player_points_assists": "Pts+Ast",
    "player_rebounds_assists": "Reb+Ast",
    # NFL
    "player_pass_yds": "Passing Yards",
    "player_pass_tds": "Passing TDs",
    "player_rush_yds": "Rushing Yards",
    "player_reception_yds": "Receiving Yards",
    "player_receptions": "Receptions",
    # MLB
    "batter_hits": "Hits",
    "batter_rbis": "RBIs",
    "pitcher_strikeouts": "Pitcher Strikeouts",
    "batter_home_runs": "Home Runs",
    # NHL
    "player_shots_on_goal": "Shots on Goal",
    "player_goals": "Goals",
    "goalie_saves": "Saves",
}

BOOKMAKERS_PRIORITY = [
    "draftkings", "fanduel", "betmgm", "caesars", "pointsbet",
    "barstool", "betrivers", "unibet_us", "betway", "espnbet",
]


@dataclass
class OddsLine:
    player_name: str
    stat_type: str
    line: float
    over_odds: float
    under_odds: float
    sportsbook: str
    event_id: str
    sport: str


class OddsAPIScraper(BaseScraper):
    def __init__(self):
        super().__init__(BASE_URL, "TheOddsAPI")

    async def get_player_props(
        self,
        sport: str,
        markets: Optional[List[str]] = None,
        bookmakers: Optional[str] = None,
    ) -> List[OddsLine]:
        """
        Fetch player prop lines for a sport.
        Returns list of OddsLine across all events for that sport.
        """
        if not settings.THE_ODDS_API_KEY:
            logger.warning("THE_ODDS_API_KEY not set — skipping odds pull")
            return []

        sport_key = SPORT_KEYS.get(sport.upper())
        if not sport_key:
            logger.warning("Unknown sport: %s", sport)
            return []

        # First get active events
        events = await self._get_events(sport_key)
        if not events:
            return []

        if markets is None:
            # Use first 5 markets to conserve API quota
            markets = list(PLAYER_PROP_MARKETS.keys())[:5]

        results: List[OddsLine] = []
        for event in events[:20]:  # cap to 20 events to conserve quota
            lines = await self._get_event_props(
                sport_key=sport_key,
                event_id=event["id"],
                markets=markets,
                bookmakers=bookmakers,
                sport=sport,
            )
            results.extend(lines)

        logger.info("TheOddsAPI: %d prop lines for %s", len(results), sport)
        return results

    async def _get_events(self, sport_key: str) -> List[Dict]:
        try:
            return await self.get(
                f"{BASE_URL}/sports/{sport_key}/events",
                params={"apiKey": settings.THE_ODDS_API_KEY},
            )
        except Exception as exc:
            logger.error("Events fetch failed for %s: %s", sport_key, exc)
            return []

    async def _get_event_props(
        self,
        sport_key: str,
        event_id: str,
        markets: List[str],
        bookmakers: Optional[str],
        sport: str,
    ) -> List[OddsLine]:
        params: Dict[str, Any] = {
            "apiKey": settings.THE_ODDS_API_KEY,
            "regions": "us",
            "markets": ",".join(markets),
            "oddsFormat": "american",
        }
        if bookmakers:
            params["bookmakers"] = bookmakers

        try:
            data = await self.get(
                f"{BASE_URL}/sports/{sport_key}/events/{event_id}/odds",
                params=params,
            )
        except Exception as exc:
            logger.debug("Prop fetch failed for event %s: %s", event_id, exc)
            return []

        return self._parse_event_props(data, sport, event_id)

    def _parse_event_props(self, data: Dict, sport: str, event_id: str) -> List[OddsLine]:
        lines: List[OddsLine] = []

        for bookmaker in data.get("bookmakers", []):
            book_key = bookmaker.get("key", "")
            for market in bookmaker.get("markets", []):
                market_key = market.get("key", "")
                stat_name = PLAYER_PROP_MARKETS.get(market_key, market_key)

                for outcome in market.get("outcomes", []):
                    # TheOddsAPI player props: description=player name, name=Over/Under
                    player_name = outcome.get("description", "")
                    direction = outcome.get("name", "")
                    price = outcome.get("price")
                    point = outcome.get("point")

                    if not player_name or price is None or point is None:
                        continue

                    # Find or create the OddsLine for this player/stat/book
                    existing = next(
                        (
                            line for line in lines
                            if line.player_name == player_name
                            and line.stat_type == stat_name
                            and line.sportsbook == book_key
                            and line.event_id == event_id
                        ),
                        None,
                    )

                    if existing:
                        if direction.lower() == "over":
                            existing.over_odds = price
                        else:
                            existing.under_odds = price
                    else:
                        over_odds = price if direction.lower() == "over" else 0.0
                        under_odds = price if direction.lower() == "under" else 0.0
                        lines.append(
                            OddsLine(
                                player_name=player_name,
                                stat_type=stat_name,
                                line=float(point),
                                over_odds=over_odds,
                                under_odds=under_odds,
                                sportsbook=book_key,
                                event_id=event_id,
                                sport=sport,
                            )
                        )

        return lines

    async def get_consensus_lines(self, sport: str) -> Dict[str, Dict[str, float]]:
        """
        Returns {player_name: {stat_type: consensus_line}} averaged across all books.
        """
        all_lines = await self.get_player_props(sport)
        consensus: Dict[str, Dict[str, List[float]]] = {}

        for line in all_lines:
            if line.player_name not in consensus:
                consensus[line.player_name] = {}
            if line.stat_type not in consensus[line.player_name]:
                consensus[line.player_name][line.stat_type] = []
            consensus[line.player_name][line.stat_type].append(line.line)

        # Average lines
        result: Dict[str, Dict[str, float]] = {}
        for player, stats in consensus.items():
            result[player] = {stat: sum(vals) / len(vals) for stat, vals in stats.items()}

        return result
