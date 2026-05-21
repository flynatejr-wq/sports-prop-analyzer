"""
WSPN (WagerSports Player News) scraper.
Fetches player props, projections, and injury news from WSPN.
Uses Playwright for JS-rendered pages + httpx for API endpoints.
"""
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

WSPN_BASE = "https://www.wspn.com"
WSPN_API_BASE = "https://api.wspn.com"

# WSPN sport identifiers
WSPN_SPORT_IDS = {
    "NBA": "basketball",
    "NFL": "football",
    "MLB": "baseball",
    "NHL": "hockey",
    "NCAAB": "college-basketball",
}


@dataclass
class WSPNProjection:
    player_id: str
    player_name: str
    team: str
    sport: str
    position: Optional[str]
    stat_type: str
    projected_value: float
    confidence: Optional[float]          # 0-100
    floor_value: Optional[float]
    ceiling_value: Optional[float]
    injury_status: Optional[str]
    injury_note: Optional[str]
    last_updated: Optional[str]
    source: str = "wspn"


@dataclass
class WSPNPlayerNews:
    player_name: str
    team: str
    sport: str
    headline: str
    detail: str
    impact_level: str              # HIGH / MEDIUM / LOW
    published_at: Optional[str]
    tags: List[str] = field(default_factory=list)


class WSPNScraper(BaseScraper):
    """
    WSPN scraper — two strategies:
    1. REST API (preferred): /api/v1/projections, /api/v1/news
    2. HTML fallback via BeautifulSoup if API returns non-JSON
    """

    def __init__(self):
        super().__init__(WSPN_API_BASE, "WSPN")
        self._wspn_headers = {
            "Accept": "application/json, text/html, */*",
            "Origin": WSPN_BASE,
            "Referer": f"{WSPN_BASE}/",
        }

    # ── Projections ───────────────────────────────────────────────────────────

    async def get_projections(self, sport: str) -> List[WSPNProjection]:
        sport_slug = WSPN_SPORT_IDS.get(sport.upper(), sport.lower())

        # Strategy 1: REST API
        try:
            data = await self.get(
                f"{WSPN_API_BASE}/projections/{sport_slug}",
                headers=self._wspn_headers,
            )
            if isinstance(data, list):
                return self._parse_api_projections(data, sport)
            if isinstance(data, dict) and "projections" in data:
                return self._parse_api_projections(data["projections"], sport)
        except Exception as exc:
            logger.debug("WSPN API projections failed for %s: %s — trying HTML", sport, exc)

        # Strategy 2: HTML scrape
        return await self._scrape_projections_html(sport_slug, sport)

    def _parse_api_projections(self, items: List[Dict], sport: str) -> List[WSPNProjection]:
        projections = []
        for item in items:
            player = item.get("player") or item
            stats = item.get("stats", {}) or item.get("projections", {})

            for stat_key, stat_value in stats.items():
                if not isinstance(stat_value, (int, float)):
                    continue
                projections.append(WSPNProjection(
                    player_id=str(player.get("id", "")),
                    player_name=player.get("name") or player.get("player_name", ""),
                    team=player.get("team") or player.get("team_abbr", ""),
                    sport=sport,
                    position=player.get("position"),
                    stat_type=self._normalize_stat_name(stat_key),
                    projected_value=float(stat_value),
                    confidence=item.get("confidence"),
                    floor_value=item.get("floor"),
                    ceiling_value=item.get("ceiling"),
                    injury_status=player.get("injury_status"),
                    injury_note=player.get("injury_note"),
                    last_updated=item.get("updated_at"),
                ))
        return projections

    async def _scrape_projections_html(self, sport_slug: str, sport: str) -> List[WSPNProjection]:
        """HTML fallback — parse WSPN projection tables."""
        try:
            html = await self.get_text(f"{WSPN_BASE}/projections/{sport_slug}")
        except Exception as exc:
            logger.error("WSPN HTML scrape failed for %s: %s", sport, exc)
            return []

        return self._parse_html_projections(html, sport)

    def _parse_html_projections(self, html: str, sport: str) -> List[WSPNProjection]:
        """
        Parse WSPN projection table rows.
        Structure: table rows with player | team | stat | projected | floor | ceiling
        """
        from bs4 import BeautifulSoup
        projections = []
        soup = BeautifulSoup(html, "lxml")

        # Find projection tables
        tables = soup.find_all("table", class_=re.compile(r"projection|prop", re.I))
        if not tables:
            tables = soup.find_all("table")

        for table in tables:
            headers_row = table.find("thead")
            if not headers_row:
                continue
            headers = [th.get_text(strip=True).lower() for th in headers_row.find_all(["th", "td"])]

            tbody = table.find("tbody")
            if not tbody:
                continue

            for row in tbody.find_all("tr"):
                cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
                if len(cells) < 3:
                    continue

                row_data = dict(zip(headers, cells)) if headers else {}

                player_name = (
                    row_data.get("player") or
                    row_data.get("name") or
                    (cells[0] if cells else "")
                )
                stat_type = (
                    row_data.get("stat") or
                    row_data.get("category") or
                    (cells[2] if len(cells) > 2 else "")
                )
                projected = row_data.get("projection") or row_data.get("projected") or (cells[3] if len(cells) > 3 else "0")

                try:
                    proj_val = float(re.sub(r"[^\d.]", "", projected))
                except (ValueError, TypeError):
                    continue

                if not player_name or proj_val <= 0:
                    continue

                projections.append(WSPNProjection(
                    player_id=f"wspn_{player_name.lower().replace(' ', '_')}",
                    player_name=player_name,
                    team=row_data.get("team", ""),
                    sport=sport,
                    position=row_data.get("pos") or row_data.get("position"),
                    stat_type=self._normalize_stat_name(stat_type),
                    projected_value=proj_val,
                    confidence=None,
                    floor_value=self._safe_float(row_data.get("floor")),
                    ceiling_value=self._safe_float(row_data.get("ceiling")),
                    injury_status=row_data.get("injury") or row_data.get("status"),
                    injury_note=None,
                    last_updated=datetime.now(timezone.utc).isoformat(),
                ))

        logger.info("WSPN: parsed %d projections from HTML for %s", len(projections), sport)
        return projections

    # ── Player News ───────────────────────────────────────────────────────────

    async def get_player_news(self, sport: str, limit: int = 50) -> List[WSPNPlayerNews]:
        sport_slug = WSPN_SPORT_IDS.get(sport.upper(), sport.lower())
        try:
            data = await self.get(
                f"{WSPN_API_BASE}/news/{sport_slug}",
                params={"limit": limit},
                headers=self._wspn_headers,
            )
            items = data if isinstance(data, list) else data.get("news", data.get("items", []))
            return self._parse_news(items, sport)
        except Exception as exc:
            logger.warning("WSPN news fetch failed for %s: %s", sport, exc)
            return []

    def _parse_news(self, items: List[Dict], sport: str) -> List[WSPNPlayerNews]:
        news = []
        for item in items:
            player_info = item.get("player") or {}
            headline = item.get("headline") or item.get("title", "")
            detail = item.get("detail") or item.get("body") or item.get("description", "")

            # Detect impact from keywords
            combined = (headline + " " + detail).lower()
            if any(k in combined for k in ["out", "surgery", "ir", "suspended", "season-ending"]):
                impact = "HIGH"
            elif any(k in combined for k in ["questionable", "limited", "gtd", "day-to-day", "reduced"]):
                impact = "MEDIUM"
            else:
                impact = "LOW"

            news.append(WSPNPlayerNews(
                player_name=player_info.get("name") or item.get("player_name", ""),
                team=player_info.get("team") or item.get("team", ""),
                sport=sport,
                headline=headline,
                detail=detail,
                impact_level=impact,
                published_at=item.get("published_at") or item.get("created_at"),
                tags=item.get("tags", []),
            ))
        return news

    # ── Playwright-based scrape (for heavily JS-rendered pages) ───────────────

    async def scrape_with_playwright(self, sport: str) -> List[WSPNProjection]:
        """
        Use Playwright when REST API and HTML scrape both fail.
        Requires: pip install playwright && playwright install chromium
        """
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("playwright not installed — skipping JS-rendered WSPN scrape")
            return []

        sport_slug = WSPN_SPORT_IDS.get(sport.upper(), sport.lower())
        url = f"{WSPN_BASE}/projections/{sport_slug}"

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800},
                )
                page = await context.new_page()

                # Intercept API responses
                intercepted: List[Dict] = []

                async def handle_response(response):
                    if "projection" in response.url.lower() and response.status == 200:
                        try:
                            body = await response.json()
                            intercepted.append(body)
                        except Exception:
                            pass

                page.on("response", handle_response)
                await page.goto(url, wait_until="networkidle", timeout=30000)

                # Try to parse intercepted API data first
                for data in intercepted:
                    items = data if isinstance(data, list) else data.get("projections", [])
                    if items:
                        await browser.close()
                        return self._parse_api_projections(items, sport)

                # Fall back to page HTML
                html = await page.content()
                await browser.close()
                return self._parse_html_projections(html, sport)

        except Exception as exc:
            logger.error("WSPN Playwright scrape failed for %s: %s", sport, exc)
            return []

    # ── Utilities ─────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_stat_name(raw: str) -> str:
        mapping = {
            "pts": "Points", "points": "Points",
            "reb": "Rebounds", "rebounds": "Rebounds", "trb": "Rebounds",
            "ast": "Assists", "assists": "Assists",
            "blk": "Blocked Shots", "blocks": "Blocked Shots",
            "stl": "Steals", "steals": "Steals",
            "tov": "Turnovers", "to": "Turnovers",
            "3pm": "3-Pointers Made", "fg3m": "3-Pointers Made", "threes": "3-Pointers Made",
            "pass_yds": "Passing Yards", "pass_yards": "Passing Yards", "passing_yards": "Passing Yards",
            "rush_yds": "Rushing Yards", "rushing_yards": "Rushing Yards",
            "rec_yds": "Receiving Yards", "receiving_yards": "Receiving Yards",
            "rec": "Receptions", "receptions": "Receptions",
            "h": "Hits", "hits": "Hits",
            "so": "Pitcher Strikeouts", "strikeouts": "Pitcher Strikeouts",
            "sog": "Shots on Goal", "shots": "Shots on Goal",
            "goals": "Goals",
            "saves": "Saves",
        }
        return mapping.get(raw.lower().strip(), raw.title())

    @staticmethod
    def _safe_float(val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(re.sub(r"[^\d.]", "", str(val)))
        except (ValueError, TypeError):
            return None
