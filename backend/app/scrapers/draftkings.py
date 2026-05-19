"""
DraftKings player props scraper.
Uses DraftKings public REST API (no auth required for props).
Endpoint discovered via browser network inspection.
"""
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

DK_API_BASE = "https://sportsbook.draftkings.com"
DK_ODDS_API = "https://sportsbook-us-ga.draftkings.com/sites/US-GA-SB/api/v5"

# DraftKings sport/category IDs for player props
DK_SPORT_CATEGORIES: Dict[str, Dict[str, int]] = {
    "NBA": {
        "sport_id": 42648,
        "sub_category_ids": {
            "Points": 583,
            "Rebounds": 584,
            "Assists": 585,
            "3-Pointers Made": 1000,
            "Pts+Reb+Ast": 1001,
            "Blocked Shots": 586,
            "Steals": 587,
        },
    },
    "NFL": {
        "sport_id": 88808,
        "sub_category_ids": {
            "Passing Yards": 492,
            "Rushing Yards": 493,
            "Receiving Yards": 494,
            "Receptions": 1002,
            "Passing TDs": 495,
        },
    },
    "MLB": {
        "sport_id": 84240,
        "sub_category_ids": {
            "Hits": 743,
            "Pitcher Strikeouts": 741,
            "Home Runs": 742,
            "RBIs": 744,
        },
    },
    "NHL": {
        "sport_id": 42133,
        "sub_category_ids": {
            "Goals": 550,
            "Shots on Goal": 549,
            "Saves": 551,
        },
    },
}

DK_HEADERS = {
    "Accept": "application/json",
    "Origin": "https://sportsbook.draftkings.com",
    "Referer": "https://sportsbook.draftkings.com/",
}


@dataclass
class DraftKingsLine:
    player_name: str
    team: str
    sport: str
    stat_type: str
    line: float
    over_odds: float
    under_odds: float
    game_id: Optional[str]
    event_name: Optional[str]
    market_id: str
    offer_id: str


class DraftKingsScraper(BaseScraper):
    def __init__(self):
        super().__init__(DK_ODDS_API, "DraftKings")

    async def get_player_props(self, sport: str) -> List[DraftKingsLine]:
        sport_config = DK_SPORT_CATEGORIES.get(sport.upper())
        if not sport_config:
            logger.warning("DraftKings: unsupported sport %s", sport)
            return []

        all_lines: List[DraftKingsLine] = []

        for stat_name, sub_cat_id in sport_config["sub_category_ids"].items():
            lines = await self._fetch_subcategory(
                sport=sport,
                sport_id=sport_config["sport_id"],
                sub_category_id=sub_cat_id,
                stat_name=stat_name,
            )
            all_lines.extend(lines)

        logger.info("DraftKings: %d prop lines for %s", len(all_lines), sport)
        return all_lines

    async def _fetch_subcategory(
        self,
        sport: str,
        sport_id: int,
        sub_category_id: int,
        stat_name: str,
    ) -> List[DraftKingsLine]:
        url = (
            f"{DK_ODDS_API}/eventgroups/{sport_id}/categories/{sub_category_id}"
            f"?format=json&includeWayTypes=true&state=US-GA&numberOfEvents=500"
        )
        try:
            data = await self.get(url, headers=DK_HEADERS)
        except Exception as exc:
            logger.debug("DK subcategory %d fetch failed: %s", sub_category_id, exc)
            return []

        return self._parse_offers(data, sport, stat_name)

    def _parse_offers(self, data: Dict, sport: str, stat_name: str) -> List[DraftKingsLine]:
        lines: List[DraftKingsLine] = []

        event_group = data.get("eventGroup") or {}
        offer_categories = event_group.get("offerCategories") or []

        for category in offer_categories:
            for sub_cat in category.get("offerSubcategoryDescriptors", []):
                for offer_cat in sub_cat.get("offerSubcategory", {}).get("offers", []):
                    for offer in offer_cat:
                        line = self._parse_single_offer(offer, sport, stat_name)
                        if line:
                            lines.append(line)

        return lines

    def _parse_single_offer(
        self, offer: Dict, sport: str, stat_name: str
    ) -> Optional[DraftKingsLine]:
        outcomes = offer.get("outcomes", [])
        if len(outcomes) < 2:
            return None

        # Find Over/Under outcomes
        over_outcome = next((o for o in outcomes if "over" in o.get("label", "").lower()), None)
        under_outcome = next((o for o in outcomes if "under" in o.get("outcomes", "").lower() or "under" in o.get("label", "").lower()), None)

        if not over_outcome:
            return None

        # Extract player name from offer label
        offer_label = offer.get("label", "")
        player_name = offer.get("participant") or offer.get("playerName") or offer_label.split(" - ")[0].strip()

        # Extract line value
        line_value = over_outcome.get("line") or over_outcome.get("points") or offer.get("line")
        if line_value is None:
            return None

        over_odds = self._dk_odds_to_american(over_outcome.get("oddsAmerican") or over_outcome.get("odds", -110))
        under_odds = self._dk_odds_to_american(
            (under_outcome.get("oddsAmerican") or under_outcome.get("odds", -110))
            if under_outcome else -110
        )

        team = offer.get("teamAbbreviation") or offer.get("team", "")

        return DraftKingsLine(
            player_name=player_name,
            team=team,
            sport=sport,
            stat_type=stat_name,
            line=float(line_value),
            over_odds=over_odds,
            under_odds=under_odds,
            game_id=str(offer.get("eventId", "")),
            event_name=offer.get("eventName", ""),
            market_id=str(offer.get("marketTypeId", "")),
            offer_id=str(offer.get("offerId", "")),
        )

    @staticmethod
    def _dk_odds_to_american(odds_value: Any) -> float:
        """DraftKings returns American odds as strings or ints."""
        if odds_value is None:
            return -110.0
        try:
            val = float(str(odds_value).replace("+", "").replace(",", ""))
            # If it looks like decimal odds (1.xx), convert
            if 1.0 < val < 10.0:
                if val >= 2.0:
                    return round((val - 1) * 100, 0)
                else:
                    return round(-100 / (val - 1), 0)
            return val
        except (ValueError, TypeError):
            return -110.0
