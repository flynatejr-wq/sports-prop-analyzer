"""
Sleeper API scraper — player projections, rankings, and news.
Free public API. Docs: https://docs.sleeper.app/
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from app.scrapers.base import BaseScraper
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SleeperProjection:
    player_id: str
    player_name: str
    team: str
    position: str
    sport: str
    # Projected stats
    pts_ppr: Optional[float]
    pts_std: Optional[float]
    passing_yards: Optional[float]
    passing_tds: Optional[float]
    rushing_yards: Optional[float]
    receiving_yards: Optional[float]
    receptions: Optional[float]
    # NBA
    pts: Optional[float]
    reb: Optional[float]
    ast: Optional[float]
    # MLB
    h: Optional[float]
    hr: Optional[float]
    rbi: Optional[float]
    so: Optional[float]  # pitcher strikeouts


class SleeperScraper(BaseScraper):
    def __init__(self):
        super().__init__(settings.SLEEPER_API_BASE, "Sleeper")
        self._players_cache: Dict[str, Dict] = {}

    async def _load_players(self, sport: str) -> Dict[str, Dict]:
        """Cache all player metadata for a sport."""
        sport_lower = sport.lower()
        cache_key = f"players_{sport_lower}"
        if cache_key in self._players_cache:
            return self._players_cache[cache_key]

        url = f"{self.base_url}/players/{sport_lower}"
        try:
            data = await self.get(url)
            self._players_cache[cache_key] = data
            return data
        except Exception as exc:
            logger.error("Sleeper players load failed for %s: %s", sport, exc)
            return {}

    async def get_projections(
        self, sport: str, season: str = "2024", week: Optional[int] = None
    ) -> List[SleeperProjection]:
        """
        Fetch Sleeper projections.
        For NFL, week is required. For season stats, use season_type='regular'.
        """
        sport_lower = sport.lower()

        if sport_lower == "nfl":
            if week is None:
                week = await self._get_current_nfl_week()
            url = f"{self.base_url}/projections/{sport_lower}/{season}/{week}"
            params = {"season_type": "regular", "position[]": ["QB", "RB", "WR", "TE"]}
        else:
            # NBA/MLB — use season projections endpoint
            url = f"{self.base_url}/projections/{sport_lower}/{season}/1"
            params = {"season_type": "regular"}

        try:
            data = await self.get(url, params=params)
        except Exception as exc:
            logger.error("Sleeper projections failed for %s: %s", sport, exc)
            return []

        players = await self._load_players(sport)
        return self._parse_projections(data, players, sport)

    def _parse_projections(
        self, data: Dict, players: Dict, sport: str
    ) -> List[SleeperProjection]:
        projections: List[SleeperProjection] = []

        for player_id, stats in data.items():
            if not isinstance(stats, dict):
                continue

            player_meta = players.get(player_id, {})
            name_parts = [
                player_meta.get("first_name", ""),
                player_meta.get("last_name", ""),
            ]
            full_name = " ".join(p for p in name_parts if p).strip()
            if not full_name:
                full_name = player_meta.get("full_name", player_id)

            projections.append(SleeperProjection(
                player_id=player_id,
                player_name=full_name,
                team=player_meta.get("team", ""),
                position=player_meta.get("position", ""),
                sport=sport,
                pts_ppr=stats.get("pts_ppr"),
                pts_std=stats.get("pts_std"),
                passing_yards=stats.get("pass_yd"),
                passing_tds=stats.get("pass_td"),
                rushing_yards=stats.get("rush_yd"),
                receiving_yards=stats.get("rec_yd"),
                receptions=stats.get("rec"),
                pts=stats.get("pts"),
                reb=stats.get("reb"),
                ast=stats.get("ast"),
                h=stats.get("h"),
                hr=stats.get("hr"),
                rbi=stats.get("rbi"),
                so=stats.get("so"),
            ))

        return projections

    async def _get_current_nfl_week(self) -> int:
        try:
            data = await self.get(f"{self.base_url}/state/nfl")
            return int(data.get("week", 1))
        except Exception:
            return 1

    async def get_player_news(self, sport: str) -> List[Dict]:
        """Trending player news from Sleeper."""
        try:
            return await self.get(f"{self.base_url}/players/{sport.lower()}/trending/add")
        except Exception:
            return []
