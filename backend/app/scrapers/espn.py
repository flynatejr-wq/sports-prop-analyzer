"""
ESPN public API scraper — game schedules, scores, and player news.
No auth required.
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.config import settings
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

SPORT_PATH = {
    "NBA": "basketball/nba",
    "NFL": "football/nfl",
    "MLB": "baseball/mlb",
    "NHL": "hockey/nhl",
    "NCAAB": "basketball/mens-college-basketball",
    "NCAAF": "football/college-football",
    "WNBA": "basketball/wnba",
}


@dataclass
class ESPNGame:
    game_id: str
    sport: str
    home_team: str
    away_team: str
    home_abbr: str
    away_abbr: str
    status: str           # scheduled, in_progress, final
    start_time: str
    home_score: Optional[int]
    away_score: Optional[int]


@dataclass
class ESPNPlayer:
    player_id: str
    name: str
    team: str
    position: str
    injury_status: Optional[str]
    injury_note: Optional[str]


class ESPNScraper(BaseScraper):
    def __init__(self):
        super().__init__(settings.ESPN_API_BASE, "ESPN")

    async def get_todays_games(self, sport: str) -> List[ESPNGame]:
        sport_path = SPORT_PATH.get(sport.upper())
        if not sport_path:
            return []
        url = f"{self.base_url}/{sport_path}/scoreboard"
        try:
            data = await self.get(url)
        except Exception as exc:
            logger.error("ESPN scoreboard failed for %s: %s", sport, exc)
            return []

        games: List[ESPNGame] = []
        for event in data.get("events", []):
            comps = event.get("competitions", [{}])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            if len(competitors) < 2:
                continue

            home = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
            away = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

            status_obj = event.get("status", {})
            status_type = status_obj.get("type", {}).get("name", "STATUS_SCHEDULED")
            if "FINAL" in status_type:
                status = "final"
            elif "IN_PROGRESS" in status_type or "LIVE" in status_type:
                status = "in_progress"
            else:
                status = "scheduled"

            games.append(ESPNGame(
                game_id=event.get("id", ""),
                sport=sport,
                home_team=home.get("team", {}).get("displayName", ""),
                away_team=away.get("team", {}).get("displayName", ""),
                home_abbr=home.get("team", {}).get("abbreviation", ""),
                away_abbr=away.get("team", {}).get("abbreviation", ""),
                status=status,
                start_time=event.get("date", ""),
                home_score=int(home.get("score", 0)) if home.get("score") else None,
                away_score=int(away.get("score", 0)) if away.get("score") else None,
            ))

        return games

    async def get_injury_report(self, sport: str) -> List[ESPNPlayer]:
        """Pull injury-tagged players from ESPN."""
        sport_path = SPORT_PATH.get(sport.upper())
        if not sport_path:
            return []

        # ESPN exposes injuries per team; get all teams then pull rosters
        url = f"{self.base_url}/{sport_path}/teams"
        try:
            data = await self.get(url)
        except Exception as exc:
            logger.error("ESPN teams failed for %s: %s", sport, exc)
            return []

        injured: List[ESPNPlayer] = []
        teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])

        for team_wrapper in teams[:32]:  # cap for speed
            team_id = team_wrapper.get("team", {}).get("id")
            if not team_id:
                continue
            team_name = team_wrapper.get("team", {}).get("displayName", "")
            players = await self._get_team_roster_injuries(sport_path, team_id, team_name)
            injured.extend(players)

        return injured

    async def _get_team_roster_injuries(
        self, sport_path: str, team_id: str, team_name: str
    ) -> List[ESPNPlayer]:
        url = f"{self.base_url}/{sport_path}/teams/{team_id}/injuries"
        try:
            data = await self.get(url)
        except Exception:
            return []

        players: List[ESPNPlayer] = []
        for item in data.get("injuries", []):
            athlete = item.get("athlete", {})
            status = item.get("status", "")
            players.append(ESPNPlayer(
                player_id=str(athlete.get("id", "")),
                name=athlete.get("displayName", ""),
                team=team_name,
                position=athlete.get("position", {}).get("abbreviation", ""),
                injury_status=status,
                injury_note=item.get("longComment") or item.get("shortComment"),
            ))
        return players

    async def get_game_pace(self, sport: str, team_abbr: str) -> Optional[float]:
        """Return recent pace metric for a team — points or possessions per game."""
        # ESPN team stats endpoint for pace-adjacent stats
        sport_path = SPORT_PATH.get(sport.upper())
        if not sport_path:
            return None

        url = f"{self.base_url}/{sport_path}/teams"
        try:
            data = await self.get(url, params={"limit": 100})
            teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
            team = next(
                (t["team"] for t in teams if t.get("team", {}).get("abbreviation", "").upper() == team_abbr.upper()),
                None,
            )
            if team:
                # Return team score avg as pace proxy — full pace data requires separate call
                stats = team.get("record", {}).get("items", [])
                if stats:
                    return float(stats[0].get("stats", [{}])[0].get("value", 0))
        except Exception:
            pass
        return None
