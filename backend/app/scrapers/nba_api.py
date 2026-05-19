"""
NBA Stats API scraper — official NBA.com stats endpoints.
Returns player game logs, season averages, and matchup data.
No auth required but requires specific headers to avoid 403.
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

NBA_STATS_BASE = "https://stats.nba.com/stats"
NBA_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Host": "stats.nba.com",
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "x-nba-stats-origin": "stats",
    "x-nba-stats-token": "true",
}

CURRENT_SEASON = "2024-25"


@dataclass
class NBAGameLog:
    player_id: int
    player_name: str
    game_date: str
    opponent: str
    is_home: bool
    points: float
    rebounds: float
    assists: float
    steals: float
    blocks: float
    turnovers: float
    three_pointers: float
    minutes: float
    usage_rate: Optional[float]


@dataclass
class NBASeasonAvg:
    player_id: int
    player_name: str
    team_abbr: str
    points: float
    rebounds: float
    assists: float
    steals: float
    blocks: float
    turnovers: float
    three_pointers: float
    minutes: float
    games_played: int


class NBAApiScraper(BaseScraper):
    def __init__(self):
        super().__init__(NBA_STATS_BASE, "NBAApi")

    async def get_player_game_log(
        self, player_id: int, season: str = CURRENT_SEASON, last_n: int = 15
    ) -> List[NBAGameLog]:
        params = {
            "PlayerID": player_id,
            "Season": season,
            "SeasonType": "Regular Season",
            "LastNGames": last_n,
        }
        try:
            data = await self.get(f"{NBA_STATS_BASE}/playergamelog", params=params, headers=NBA_HEADERS)
        except Exception as exc:
            logger.error("NBA game log failed for player %d: %s", player_id, exc)
            return []

        return self._parse_game_log(data)

    def _parse_game_log(self, data: Dict) -> List[NBAGameLog]:
        logs = []
        result_sets = data.get("resultSets", [])
        if not result_sets:
            return logs

        rs = result_sets[0]
        headers = [h.upper() for h in rs.get("headers", [])]
        rows = rs.get("rowSet", [])

        def col(row: list, name: str) -> Any:
            try:
                return row[headers.index(name)]
            except (ValueError, IndexError):
                return None

        for row in rows:
            matchup = col(row, "MATCHUP") or ""
            is_home = "vs." in matchup
            opponent = matchup.split(" ")[-1] if matchup else ""

            logs.append(NBAGameLog(
                player_id=col(row, "PLAYER_ID") or 0,
                player_name=col(row, "PLAYER_NAME") or "",
                game_date=col(row, "GAME_DATE") or "",
                opponent=opponent,
                is_home=is_home,
                points=float(col(row, "PTS") or 0),
                rebounds=float(col(row, "REB") or 0),
                assists=float(col(row, "AST") or 0),
                steals=float(col(row, "STL") or 0),
                blocks=float(col(row, "BLK") or 0),
                turnovers=float(col(row, "TOV") or 0),
                three_pointers=float(col(row, "FG3M") or 0),
                minutes=self._parse_minutes(col(row, "MIN")),
                usage_rate=None,
            ))

        return logs

    @staticmethod
    def _parse_minutes(min_str: Optional[str]) -> float:
        """Convert '32:14' to 32.23."""
        if min_str is None:
            return 0.0
        if isinstance(min_str, (int, float)):
            return float(min_str)
        try:
            parts = str(min_str).split(":")
            return float(parts[0]) + float(parts[1]) / 60 if len(parts) == 2 else float(parts[0])
        except (ValueError, IndexError):
            return 0.0

    async def get_season_averages(self, season: str = CURRENT_SEASON) -> List[NBASeasonAvg]:
        """Get per-game season averages for all players."""
        params = {
            "Season": season,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
        }
        try:
            data = await self.get(f"{NBA_STATS_BASE}/leaguedashplayerstats", params=params, headers=NBA_HEADERS)
        except Exception as exc:
            logger.error("NBA season averages failed: %s", exc)
            return []

        return self._parse_season_averages(data)

    def _parse_season_averages(self, data: Dict) -> List[NBASeasonAvg]:
        avgs = []
        result_sets = data.get("resultSets", [])
        if not result_sets:
            return avgs

        rs = result_sets[0]
        headers = [h.upper() for h in rs.get("headers", [])]
        rows = rs.get("rowSet", [])

        def col(row: list, name: str) -> Any:
            try:
                return row[headers.index(name)]
            except (ValueError, IndexError):
                return None

        for row in rows:
            avgs.append(NBASeasonAvg(
                player_id=col(row, "PLAYER_ID") or 0,
                player_name=col(row, "PLAYER_NAME") or "",
                team_abbr=col(row, "TEAM_ABBREVIATION") or "",
                points=float(col(row, "PTS") or 0),
                rebounds=float(col(row, "REB") or 0),
                assists=float(col(row, "AST") or 0),
                steals=float(col(row, "STL") or 0),
                blocks=float(col(row, "BLK") or 0),
                turnovers=float(col(row, "TOV") or 0),
                three_pointers=float(col(row, "FG3M") or 0),
                minutes=float(col(row, "MIN") or 0),
                games_played=int(col(row, "GP") or 0),
            ))

        return avgs

    async def get_team_defense_ratings(self, season: str = CURRENT_SEASON) -> Dict[str, float]:
        """Returns {team_abbr: opp_pts_per_game} — used as defensive matchup factor."""
        params = {
            "Season": season,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "MeasureType": "Opponent",
        }
        try:
            data = await self.get(f"{NBA_STATS_BASE}/leaguedashteamstats", params=params, headers=NBA_HEADERS)
        except Exception as exc:
            logger.error("NBA team defense ratings failed: %s", exc)
            return {}

        ratings: Dict[str, float] = {}
        rs = data.get("resultSets", [{}])[0]
        headers = [h.upper() for h in rs.get("headers", [])]
        for row in rs.get("rowSet", []):
            try:
                abbr = row[headers.index("TEAM_ABBREVIATION")]
                opp_pts = float(row[headers.index("OPP_PTS")])
                ratings[abbr] = opp_pts
            except (ValueError, IndexError):
                continue

        return ratings

    async def get_player_usage(self, season: str = CURRENT_SEASON) -> Dict[int, float]:
        """Returns {player_id: usage_rate} for the current season."""
        params = {
            "Season": season,
            "SeasonType": "Regular Season",
            "PerMode": "PerGame",
            "MeasureType": "Advanced",
        }
        try:
            data = await self.get(f"{NBA_STATS_BASE}/leaguedashplayerstats", params=params, headers=NBA_HEADERS)
        except Exception as exc:
            logger.error("NBA usage rates failed: %s", exc)
            return {}

        usage: Dict[int, float] = {}
        rs = data.get("resultSets", [{}])[0]
        headers = [h.upper() for h in rs.get("headers", [])]
        for row in rs.get("rowSet", []):
            try:
                pid = int(row[headers.index("PLAYER_ID")])
                usg = float(row[headers.index("USG_PCT")])
                usage[pid] = usg * 100  # convert to %
            except (ValueError, IndexError):
                continue

        return usage
