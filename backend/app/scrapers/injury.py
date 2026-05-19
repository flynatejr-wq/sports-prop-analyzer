"""
Injury report scraper — pulls from Rotowire and ESPN RSS/API.
Returns structured injury data for all active sports.
"""
import logging
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from app.scrapers.base import BaseScraper
from app.config import settings

logger = logging.getLogger(__name__)

ROTOWIRE_INJURY_URLS = {
    "NBA": "https://www.rotowire.com/basketball/nba-injuries.php",
    "NFL": "https://www.rotowire.com/football/nfl-injuries.php",
    "MLB": "https://www.rotowire.com/baseball/mlb-injuries.php",
    "NHL": "https://www.rotowire.com/hockey/nhl-injuries.php",
}

ROTOWIRE_NEWS_URLS = {
    "NBA": "https://www.rotowire.com/basketball/rss.php",
    "NFL": "https://www.rotowire.com/football/rss.php",
    "MLB": "https://www.rotowire.com/baseball/rss.php",
    "NHL": "https://www.rotowire.com/hockey/rss.php",
}


@dataclass
class InjuryReport:
    player_name: str
    team: str
    sport: str
    status: str           # OUT, GTD, QUESTIONABLE, PROBABLE, IR, DNP
    injury_type: Optional[str]
    note: Optional[str]
    source: str           # rotowire, espn


@dataclass
class PlayerNews:
    player_name: str
    team: str
    sport: str
    headline: str
    analysis: Optional[str]
    impact: Optional[str]   # HIGH, MEDIUM, LOW


class InjuryScraper(BaseScraper):
    def __init__(self):
        super().__init__(settings.ROTOWIRE_BASE, "InjuryFeed")

    async def get_all_injuries(self, sport: str) -> List[InjuryReport]:
        """Pull injury report for a sport from Rotowire."""
        url = ROTOWIRE_INJURY_URLS.get(sport.upper())
        if not url:
            return []

        try:
            html = await self.get_text(url)
        except Exception as exc:
            logger.error("Injury scrape failed for %s: %s", sport, exc)
            return []

        return self._parse_rotowire_injuries(html, sport)

    def _parse_rotowire_injuries(self, html: str, sport: str) -> List[InjuryReport]:
        """
        Parse Rotowire injury table HTML.
        Structure: each player row has name, team, position, injury, status, note columns.
        """
        injuries: List[InjuryReport] = []

        # Find injury rows — Rotowire uses consistent class names
        row_pattern = re.compile(
            r'<tr[^>]*class="[^"]*player[^"]*"[^>]*>(.*?)</tr>',
            re.DOTALL | re.IGNORECASE,
        )
        cell_pattern = re.compile(r'<td[^>]*>(.*?)</td>', re.DOTALL | re.IGNORECASE)
        strip_tags = re.compile(r'<[^>]+>')

        def clean(text: str) -> str:
            return strip_tags.sub("", text).strip()

        for row_match in row_pattern.finditer(html):
            cells = [clean(c.group(1)) for c in cell_pattern.finditer(row_match.group(1))]
            if len(cells) < 4:
                continue

            # Rotowire column order varies slightly; try to identify by content
            player_name = cells[0] if cells[0] else ""
            team = cells[1] if len(cells) > 1 else ""
            injury_type = cells[3] if len(cells) > 3 else ""
            status = cells[4] if len(cells) > 4 else ""
            note = cells[5] if len(cells) > 5 else ""

            if not player_name or not status:
                continue

            # Normalize status
            status_upper = status.upper()
            normalized_status = "OUT"
            if "OUT" in status_upper:
                normalized_status = "OUT"
            elif "GTD" in status_upper or "GAME TIME" in status_upper:
                normalized_status = "GTD"
            elif "QUESTIONABLE" in status_upper:
                normalized_status = "QUESTIONABLE"
            elif "PROBABLE" in status_upper:
                normalized_status = "PROBABLE"
            elif "IR" in status_upper or "IL" in status_upper:
                normalized_status = "IR"
            elif "DNP" in status_upper:
                normalized_status = "DNP"

            injuries.append(InjuryReport(
                player_name=player_name,
                team=team,
                sport=sport,
                status=normalized_status,
                injury_type=injury_type or None,
                note=note or None,
                source="rotowire",
            ))

        logger.info("Rotowire: %d injuries parsed for %s", len(injuries), sport)
        return injuries

    async def get_player_news(self, sport: str) -> List[PlayerNews]:
        """Parse Rotowire RSS news feed for player news / usage impacts."""
        url = ROTOWIRE_NEWS_URLS.get(sport.upper())
        if not url:
            return []

        try:
            xml = await self.get_text(url)
        except Exception as exc:
            logger.error("News feed failed for %s: %s", sport, exc)
            return []

        return self._parse_news_rss(xml, sport)

    def _parse_news_rss(self, xml: str, sport: str) -> List[PlayerNews]:
        news: List[PlayerNews] = []
        strip_tags = re.compile(r'<[^>]+>')

        # Extract RSS items
        items = re.findall(r'<item>(.*?)</item>', xml, re.DOTALL)
        for item in items[:50]:
            title = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
            description = re.search(r'<description>(.*?)</description>', item, re.DOTALL)

            if not title:
                continue

            headline = strip_tags.sub("", title.group(1)).strip()
            desc = strip_tags.sub("", description.group(1)).strip() if description else ""

            # Extract player name (first part before " -" or the full title)
            player_match = re.match(r'^([A-Z][a-zA-Z\'-]+\s+[A-Z][a-zA-Z\'-]+)', headline)
            player_name = player_match.group(1) if player_match else headline[:50]

            # Heuristic impact detection
            impact = "LOW"
            high_keywords = ["out", "injured reserve", "season-ending", "surgery", "suspended"]
            med_keywords = ["questionable", "limited", "gtd", "day-to-day", "reduced role"]
            desc_lower = desc.lower()
            headline_lower = headline.lower()
            combined = desc_lower + headline_lower

            if any(kw in combined for kw in high_keywords):
                impact = "HIGH"
            elif any(kw in combined for kw in med_keywords):
                impact = "MEDIUM"

            news.append(PlayerNews(
                player_name=player_name,
                team="",   # Rotowire RSS doesn't always include team in XML
                sport=sport,
                headline=headline,
                analysis=desc if len(desc) > 20 else None,
                impact=impact,
            ))

        return news

    async def get_all_sports_injuries(self) -> Dict[str, List[InjuryReport]]:
        """Fetch injuries for all supported sports concurrently."""
        import asyncio
        sports = ["NBA", "NFL", "MLB", "NHL"]
        results = await asyncio.gather(*[self.get_all_injuries(s) for s in sports])
        return dict(zip(sports, results))
