"""
FanDuel player props scraper.
Uses FanDuel's public content API — no auth required.
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

FD_API_BASE = "https://sbapi.tn.sportsbook.fanduel.com/api"

# FanDuel competition IDs for player props
FD_COMPETITIONS: Dict[str, int] = {
    "NBA": 7523,
    "NFL": 11,
    "MLB": 9,
    "NHL": 6,
    "NCAAB": 77,
}

# FD market names that map to player props
FD_PLAYER_PROP_MARKETS = {
    "Player Points": "Points",
    "Player Rebounds": "Rebounds",
    "Player Assists": "Assists",
    "Player Threes": "3-Pointers Made",
    "Player Blocks": "Blocked Shots",
    "Player Steals": "Steals",
    "Player Turnovers": "Turnovers",
    "Player Points + Rebounds + Assists": "Pts+Reb+Ast",
    "Player Passing Yards": "Passing Yards",
    "Player Rushing Yards": "Rushing Yards",
    "Player Receiving Yards": "Receiving Yards",
    "Player Receptions": "Receptions",
    "Batter Hits": "Hits",
    "Pitcher Strikeouts": "Pitcher Strikeouts",
    "Player Goals": "Goals",
    "Player Shots On Target": "Shots on Goal",
    "Goaltender Saves": "Saves",
}

FD_HEADERS = {
    "Accept": "application/json",
    "Origin": "https://sportsbook.fanduel.com",
    "Referer": "https://sportsbook.fanduel.com/",
}


@dataclass
class FanDuelLine:
    player_name: str
    team: str
    sport: str
    stat_type: str
    line: float
    over_odds: float
    under_odds: float
    event_id: str
    market_id: str
    is_sgp_eligible: bool = False


class FanDuelScraper(BaseScraper):
    def __init__(self):
        super().__init__(FD_API_BASE, "FanDuel")

    async def get_player_props(self, sport: str) -> List[FanDuelLine]:
        competition_id = FD_COMPETITIONS.get(sport.upper())
        if not competition_id:
            logger.warning("FanDuel: unsupported sport %s", sport)
            return []

        # Fetch events for the competition
        events = await self._get_events(competition_id)
        if not events:
            return []

        all_lines: List[FanDuelLine] = []
        for event_id in events[:30]:   # cap per refresh cycle
            lines = await self._get_event_props(event_id, sport)
            all_lines.extend(lines)

        logger.info("FanDuel: %d prop lines for %s", len(all_lines), sport)
        return all_lines

    async def _get_events(self, competition_id: int) -> List[str]:
        try:
            data = await self.get(
                f"{FD_API_BASE}/content-managed-page",
                params={
                    "page": "COMPETITION",
                    "competitionId": competition_id,
                    "includeMarkets": "false",
                    "timezone": "America/New_York",
                },
                headers=FD_HEADERS,
            )
        except Exception as exc:
            logger.error("FanDuel events fetch failed for comp %d: %s", competition_id, exc)
            return []

        events = []
        for event in data.get("attachments", {}).get("events", {}).values():
            events.append(str(event.get("eventId", "")))
        return [e for e in events if e]

    async def _get_event_props(self, event_id: str, sport: str) -> List[FanDuelLine]:
        try:
            data = await self.get(
                f"{FD_API_BASE}/content-managed-page",
                params={
                    "page": "EVENT",
                    "eventId": event_id,
                    "includeMarkets": "true",
                    "timezone": "America/New_York",
                },
                headers=FD_HEADERS,
            )
        except Exception as exc:
            logger.debug("FanDuel event %s props failed: %s", event_id, exc)
            return []

        return self._parse_event_markets(data, event_id, sport)

    def _parse_event_markets(self, data: Dict, event_id: str, sport: str) -> List[FanDuelLine]:
        lines: List[FanDuelLine] = []
        markets = data.get("attachments", {}).get("markets", {})

        for market_id, market in markets.items():
            market_name = market.get("marketName", "")
            stat_type = FD_PLAYER_PROP_MARKETS.get(market_name)
            if not stat_type:
                # Try partial match
                stat_type = next(
                    (v for k, v in FD_PLAYER_PROP_MARKETS.items()
                     if k.lower() in market_name.lower()),
                    None,
                )
            if not stat_type:
                continue

            runners = market.get("runners", [])
            # Group by handicap (the line value)
            handicaps: Dict[float, Dict] = {}
            for runner in runners:
                handicap = runner.get("handicap")
                if handicap is None:
                    continue
                handicap = float(handicap)
                if handicap not in handicaps:
                    handicaps[handicap] = {"over": None, "under": None, "runner": runner}

                label = runner.get("runnerName", "").lower()
                price = self._extract_price(runner)
                if "over" in label:
                    handicaps[handicap]["over"] = price
                elif "under" in label:
                    handicaps[handicap]["under"] = price

            for handicap, data_h in handicaps.items():
                runner = data_h["runner"]
                player_name = self._extract_player_name(runner, market_name)
                if not player_name:
                    continue

                lines.append(FanDuelLine(
                    player_name=player_name,
                    team=runner.get("teamAbbreviation") or runner.get("teamName", ""),
                    sport=sport,
                    stat_type=stat_type,
                    line=handicap,
                    over_odds=data_h["over"] or -110.0,
                    under_odds=data_h["under"] or -110.0,
                    event_id=event_id,
                    market_id=market_id,
                    is_sgp_eligible=market.get("sgpEligible", False),
                ))

        return lines

    @staticmethod
    def _extract_price(runner: Dict) -> float:
        """Extract American odds from FanDuel runner."""
        prices = runner.get("prices", [])
        if not prices:
            return -110.0
        price = prices[0]
        american = price.get("americanOdds") or price.get("price")
        if american is None:
            # Convert from decimal
            decimal = price.get("decimalOdds") or price.get("decimal")
            if decimal:
                if float(decimal) >= 2.0:
                    return round((float(decimal) - 1) * 100)
                else:
                    return round(-100 / (float(decimal) - 1))
        return float(american or -110)

    @staticmethod
    def _extract_player_name(runner: Dict, market_name: str) -> Optional[str]:
        name = runner.get("runnerName") or runner.get("playerName")
        if not name:
            return None
        # Strip "Over/Under X.X" suffix if present
        import re
        name = re.sub(r"\s+(Over|Under)\s+[\d.]+$", "", name, flags=re.I).strip()
        return name if name else None
