"""
Prop analysis orchestrator — ties together scrapers, EV calculator,
and ML predictions to produce enriched Prop objects ready for the DB.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from difflib import SequenceMatcher

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.prop import Prop, PropStatus
from app.models.player import Player, PlayerStats
from app.models.odds import SbookLine
from app.scrapers.prizepicks import PrizePicksScraper, PrizePicksProjection
from app.scrapers.odds_api import OddsAPIScraper, OddsLine
from app.scrapers.nba_api import NBAApiScraper
from app.scrapers.espn import ESPNScraper
from app.scrapers.injury import InjuryScraper
from app.services import ev_calculator as ev
from app.config import settings
from app.utils.cache import cache

logger = logging.getLogger(__name__)


def _name_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _match_player(pp_name: str, candidates: List[str]) -> Optional[str]:
    """Fuzzy match a PrizePicks player name to a sportsbook player name."""
    best_score = 0.0
    best_match = None
    for name in candidates:
        score = _name_similarity(pp_name, name)
        if score > best_score:
            best_score = score
            best_match = name
    return best_match if best_score >= 0.80 else None


class PropAnalyzer:
    def __init__(self):
        self.pp_scraper = PrizePicksScraper()
        self.odds_scraper = OddsAPIScraper()
        self.nba_scraper = NBAApiScraper()
        self.espn_scraper = ESPNScraper()
        self.injury_scraper = InjuryScraper()

    async def run_full_analysis(self, db: AsyncSession, sports: Optional[List[str]] = None) -> List[Dict]:
        """
        Main entry point — runs the complete analysis pipeline.
        Returns list of enriched prop dicts for all sports.
        """
        if sports is None:
            sports = ["NBA", "NFL", "MLB", "NHL"]

        logger.info("Starting full prop analysis for sports: %s", sports)

        # Fetch PrizePicks projections
        pp_projections = await self.pp_scraper.get_all_sports()
        if not pp_projections:
            logger.warning("No PrizePicks projections returned")
            return []

        # Fetch sportsbook odds for each sport
        sbook_lines: Dict[str, List[OddsLine]] = {}
        injury_map: Dict[str, str] = {}

        tasks = []
        for sport in sports:
            tasks.append(self._fetch_sport_data(sport))

        sport_data_results = await asyncio.gather(*tasks, return_exceptions=True)
        for sport, result in zip(sports, sport_data_results):
            if isinstance(result, Exception):
                logger.error("Sport data fetch failed for %s: %s", sport, result)
                sbook_lines[sport] = []
            else:
                sbook_lines[sport], injuries = result
                injury_map.update(injuries)

        # Build consensus line map: {(player_name, stat_type): avg_line}
        consensus_map = self._build_consensus_map(sbook_lines)

        # Analyze each prop
        enriched_props = []
        for proj in pp_projections:
            try:
                prop_data = await self._analyze_projection(proj, consensus_map, injury_map, db)
                if prop_data:
                    enriched_props.append(prop_data)
            except Exception as exc:
                logger.warning("Failed to analyze prop %s %s: %s", proj.player_name, proj.stat_type, exc)

        # Sort by absolute EV descending
        enriched_props.sort(key=lambda p: abs(p.get("ev_over") or 0), reverse=True)

        # Upsert to database
        await self._upsert_props(db, enriched_props)
        logger.info("Analysis complete: %d props enriched", len(enriched_props))
        return enriched_props

    async def _fetch_sport_data(self, sport: str) -> Tuple[List[OddsLine], Dict[str, str]]:
        """Fetch sportsbook lines and injury statuses for a sport."""
        odds_task = self.odds_scraper.get_player_props(sport)
        injury_task = self.injury_scraper.get_all_injuries(sport)

        odds, injuries = await asyncio.gather(odds_task, injury_task, return_exceptions=True)

        if isinstance(odds, Exception):
            logger.error("Odds fetch failed for %s: %s", sport, odds)
            odds = []
        if isinstance(injuries, Exception):
            injuries = []

        # Build {player_name_lower: status}
        injury_map = {
            i.player_name.lower(): i.status
            for i in (injuries or [])
        }

        return odds, injury_map

    def _build_consensus_map(
        self, sbook_lines: Dict[str, List[OddsLine]]
    ) -> Dict[Tuple[str, str], Dict]:
        """
        Build consensus map across all sportsbooks.
        Key: (player_name_lower, stat_type_lower)
        Value: {avg_line, lines_by_book, avg_over_odds, avg_under_odds}
        """
        accumulator: Dict[Tuple[str, str], Dict[str, List]] = {}

        for sport, lines in sbook_lines.items():
            for line in lines:
                key = (line.player_name.lower(), line.stat_type.lower())
                if key not in accumulator:
                    accumulator[key] = {"lines": [], "over_odds": [], "under_odds": [], "books": {}}
                accumulator[key]["lines"].append(line.line)
                if line.over_odds:
                    accumulator[key]["over_odds"].append(line.over_odds)
                if line.under_odds:
                    accumulator[key]["under_odds"].append(line.under_odds)
                accumulator[key]["books"][line.sportsbook] = line.line

        consensus: Dict[Tuple[str, str], Dict] = {}
        for key, data in accumulator.items():
            lines_list = data["lines"]
            if not lines_list:
                continue
            avg_line = sum(lines_list) / len(lines_list)
            avg_over = sum(data["over_odds"]) / len(data["over_odds"]) if data["over_odds"] else -110.0
            avg_under = sum(data["under_odds"]) / len(data["under_odds"]) if data["under_odds"] else -110.0
            consensus[key] = {
                "avg_line": avg_line,
                "avg_over_odds": avg_over,
                "avg_under_odds": avg_under,
                "num_books": len(lines_list),
                "books": data["books"],
            }

        return consensus

    async def _analyze_projection(
        self,
        proj: PrizePicksProjection,
        consensus_map: Dict,
        injury_map: Dict[str, str],
        db: AsyncSession,
    ) -> Optional[Dict]:
        """Enrich a single PrizePicks projection with EV analysis."""

        # Find matching consensus line (fuzzy name match)
        player_lower = proj.player_name.lower()
        stat_lower = proj.stat_type.lower()

        # Direct key lookup first
        direct_key = (player_lower, stat_lower)
        consensus_data = consensus_map.get(direct_key)

        # Fuzzy match if direct not found
        if not consensus_data:
            all_names = {k[0] for k in consensus_map.keys() if k[1] == stat_lower}
            matched_name = _match_player(player_lower, list(all_names))
            if matched_name:
                consensus_data = consensus_map.get((matched_name, stat_lower))

        consensus_line = consensus_data["avg_line"] if consensus_data else None
        avg_over_odds = consensus_data["avg_over_odds"] if consensus_data else -110.0
        avg_under_odds = consensus_data["avg_under_odds"] if consensus_data else -110.0

        # Get historical stats for this player
        stat_history = await self._get_player_stat_history(proj.player_name, proj.stat_type, proj.sport, db)
        last_5 = stat_history.get("last_5", [])
        season_avg = stat_history.get("season_avg", 0.0)
        home_avg = stat_history.get("home_avg")
        away_avg = stat_history.get("away_avg")

        # Matchup adjustment based on opponent defensive rating
        matchup_adj = await self._get_matchup_adjustment(proj.sport, proj.opponent, proj.stat_type)

        # Calculate fair probability
        fair_prob_over = ev.hit_rate_to_fair_prob(
            last_5=last_5,
            season_avg=season_avg,
            line=proj.line,
            home_avg=home_avg,
            away_avg=away_avg,
            is_home=True,
            matchup_adjustment=matchup_adj,
        )

        # EV calculation — PrizePicks single picks
        ev_over = ev.prizepicks_ev(fair_prob_over)
        ev_under = ev.prizepicks_ev(1 - fair_prob_over)

        # Vs sportsbook odds EV
        ev_over_vs_book = ev.calculate_ev(fair_prob_over, avg_over_odds) if avg_over_odds else None
        ev_under_vs_book = ev.calculate_ev(1 - fair_prob_over, avg_under_odds) if avg_under_odds else None

        # Line discrepancy
        disc = ev.calculate_line_discrepancy(proj.line, consensus_line) if consensus_line else None

        # Stale line detection
        is_stale = ev.is_stale_line(proj.line, consensus_line) if consensus_line else False

        # Implied probability from the line itself
        imp_over, imp_under = ev.calculate_implied_prob_from_line(proj.line, season_avg)

        # Hit rate over last N games
        hit_rate = sum(1 for g in last_5 if g > proj.line) / len(last_5) if last_5 else None

        # Injury status
        injury_status = injury_map.get(player_lower)

        return {
            "player_name": proj.player_name,
            "team": proj.team,
            "sport": proj.sport,
            "league": proj.league,
            "position": proj.position,
            "image_url": proj.image_url,
            "stat_type": proj.stat_type,
            "line": proj.line,
            "source": "prizepicks",
            "external_id": proj.projection_id,
            "game_date": proj.start_time[:10] if proj.start_time else None,
            "opponent": proj.opponent,
            "is_boosted": proj.is_boosted,
            # EV
            "ev_over": ev_over,
            "ev_under": ev_under,
            "ev_over_vs_book": ev_over_vs_book,
            "ev_under_vs_book": ev_under_vs_book,
            "edge_classification": ev.classify_edge(max(ev_over, ev_under)),
            # Consensus
            "consensus_line": consensus_line,
            "fair_value": season_avg,
            "line_discrepancy": disc,
            "implied_prob_over": imp_over,
            "implied_prob_under": imp_under,
            "fair_prob_over": fair_prob_over,
            "is_stale": is_stale,
            # History
            "last_5_avg": sum(last_5) / len(last_5) if last_5 else None,
            "season_avg": season_avg,
            "home_avg": home_avg,
            "away_avg": away_avg,
            "hit_rate_over": hit_rate,
            # Context
            "injury_status": injury_status,
            "matchup_adjustment": matchup_adj,
        }

    async def _get_player_stat_history(
        self, player_name: str, stat_type: str, sport: str, db: AsyncSession
    ) -> Dict[str, Any]:
        """Pull historical stats from DB; fall back to NBA API if empty."""
        stat_col = self._stat_type_to_column(stat_type)
        if not stat_col:
            return {}

        # Query DB for last 15 games
        result = await db.execute(
            select(Player.id)
            .where(Player.name.ilike(f"%{player_name}%"), Player.sport == sport)
            .limit(1)
        )
        player_row = result.scalar_one_or_none()

        if not player_row:
            return {}

        stats_result = await db.execute(
            select(PlayerStats)
            .where(PlayerStats.player_id == player_row)
            .order_by(PlayerStats.game_date.desc())
            .limit(15)
        )
        stats = stats_result.scalars().all()

        if not stats:
            return {}

        values = [getattr(s, stat_col) for s in stats if getattr(s, stat_col) is not None]
        last_5 = values[:5]
        season_avg = sum(values) / len(values) if values else 0.0
        home_vals = [getattr(s, stat_col) for s in stats if s.is_home and getattr(s, stat_col)]
        away_vals = [getattr(s, stat_col) for s in stats if not s.is_home and getattr(s, stat_col)]

        return {
            "last_5": last_5,
            "season_avg": season_avg,
            "home_avg": sum(home_vals) / len(home_vals) if home_vals else None,
            "away_avg": sum(away_vals) / len(away_vals) if away_vals else None,
        }

    @staticmethod
    def _stat_type_to_column(stat_type: str) -> Optional[str]:
        mapping = {
            "points": "points",
            "pts": "points",
            "rebounds": "rebounds",
            "reb": "rebounds",
            "assists": "assists",
            "ast": "assists",
            "3-pointers made": "three_pointers",
            "blocked shots": "blocks",
            "steals": "steals",
            "turnovers": "turnovers",
            "passing yards": "passing_yards",
            "rushing yards": "rushing_yards",
            "receiving yards": "receiving_yards",
            "receptions": "receptions",
            "hits": "hits",
            "pitcher strikeouts": "strikeouts",
            "shots on goal": "shots_on_goal",
            "goals": "goals",
            "saves": "saves",
        }
        return mapping.get(stat_type.lower())

    async def _get_matchup_adjustment(
        self, sport: str, opponent: Optional[str], stat_type: str
    ) -> float:
        """Return adjustment in % based on opponent defensive rating. Cached."""
        if not opponent or sport != "NBA":
            return 0.0

        cache_key = f"def_rating:{sport}"
        ratings = await cache.get(cache_key)
        if ratings is None:
            try:
                ratings = await self.nba_scraper.get_team_defense_ratings()
                await cache.set(cache_key, ratings, ttl=3600)
            except Exception:
                return 0.0

        league_avg = 111.5  # NBA league avg opponent points per game
        opp_rating = ratings.get(opponent.upper(), league_avg)
        # Each point above/below league avg → ~1% adjustment for scoring props
        return round((opp_rating - league_avg) * 0.8, 1)

    async def _upsert_props(self, db: AsyncSession, prop_dicts: List[Dict]):
        """Insert new props or update existing ones by external_id."""
        for p in prop_dicts:
            external_id = p.get("external_id")
            if not external_id:
                continue

            result = await db.execute(
                select(Prop).where(Prop.external_id == external_id, Prop.source == "prizepicks")
            )
            existing = result.scalar_one_or_none()

            if existing:
                for field in ["ev_over", "ev_under", "consensus_line", "line_discrepancy", "is_stale",
                               "last_5_avg", "season_avg", "hit_rate_over", "fair_value",
                               "implied_prob_over", "implied_prob_under"]:
                    if field in p:
                        setattr(existing, field, p[field])
            else:
                # Resolve or create player
                player = await self._get_or_create_player(db, p)
                if not player:
                    continue
                new_prop = Prop(
                    player_id=player.id,
                    source="prizepicks",
                    external_id=external_id,
                    sport=p["sport"],
                    league=p.get("league"),
                    game_date=p.get("game_date"),
                    opponent=p.get("opponent"),
                    stat_type=p["stat_type"],
                    line=p["line"],
                    ev_over=p.get("ev_over"),
                    ev_under=p.get("ev_under"),
                    consensus_line=p.get("consensus_line"),
                    line_discrepancy=p.get("line_discrepancy"),
                    fair_value=p.get("fair_value"),
                    implied_prob_over=p.get("implied_prob_over"),
                    implied_prob_under=p.get("implied_prob_under"),
                    is_stale=p.get("is_stale", False),
                    is_boosted=p.get("is_boosted", False),
                    last_5_avg=p.get("last_5_avg"),
                    season_avg=p.get("season_avg"),
                    home_avg=p.get("home_avg"),
                    away_avg=p.get("away_avg"),
                    hit_rate_over=p.get("hit_rate_over"),
                )
                db.add(new_prop)

        await db.flush()

    async def _get_or_create_player(self, db: AsyncSession, p: Dict) -> Optional[Player]:
        result = await db.execute(
            select(Player).where(
                Player.name.ilike(f"%{p['player_name']}%"),
                Player.sport == p["sport"],
            ).limit(1)
        )
        player = result.scalar_one_or_none()
        if not player:
            player = Player(
                external_id=f"pp_{p.get('external_id', '')}",
                name=p["player_name"],
                sport=p["sport"],
                team=p.get("team"),
                position=p.get("position"),
                image_url=p.get("image_url"),
                injury_status=p.get("injury_status"),
            )
            db.add(player)
            await db.flush()
        return player
