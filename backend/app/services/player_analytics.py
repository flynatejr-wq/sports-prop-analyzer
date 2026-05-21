"""
Player analytics engine — weighted projection system.
Synthesizes recent form, season averages, home/away splits,
pace, usage, matchup, and injury impact into a single projected value.
"""
import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PlayerProjection:
    player_name: str
    stat_type: str
    projected_value: float
    floor: float
    ceiling: float
    confidence: float           # 0-100
    volatility: float           # 0-1, higher = more uncertain
    components: Dict[str, float]  # breakdown of what drove the projection
    trend: str                  # "HOT", "COLD", "NEUTRAL"
    matchup_grade: str          # "A", "B", "C", "D", "F"
    recommendation: str         # "STRONG OVER", "LEAN OVER", "LEAN UNDER", "STRONG UNDER", "PASS"
    reasoning: List[str]


def weighted_projection(
    last_5: List[float],
    last_10: List[float],
    season_avg: float,
    home_avg: Optional[float],
    away_avg: Optional[float],
    is_home: bool,
    usage_current: float = 20.0,      # current season usage %
    usage_season: float = 20.0,       # full season usage %
    opp_def_rating: float = 0.0,      # opponent defensive rating (percentile, 0=worst, 100=best)
    pace_factor: float = 1.0,         # team pace relative to league avg (1.0 = league avg)
    minutes_projection: Optional[float] = None,
    minutes_season_avg: float = 30.0,
    injury_reduction: float = 0.0,    # % reduction due to injury concerns (0-1)
) -> PlayerProjection:
    """
    Build a weighted projection with components:
    - recent_form (40%)
    - season_baseline (25%)
    - location_split (15%)
    - matchup_adjustment (10%)
    - pace_usage_adjustment (10%)
    """
    reasoning: List[str] = []

    # ── Recent form ──────────────────────────────────────────────────────────
    recent_avg = sum(last_5) / len(last_5) if last_5 else season_avg
    _l10_avg = sum(last_10) / len(last_10) if last_10 else season_avg  # reserved for future use

    # Trend detection
    if len(last_5) >= 3:
        # Slope of last 5 (positive = trending up)
        x = list(range(len(last_5)))
        n = len(x)
        xy = sum(xi * yi for xi, yi in zip(x, last_5))
        sx = sum(x)
        sy = sum(last_5)
        sx2 = sum(xi ** 2 for xi in x)
        slope = (n * xy - sx * sy) / (n * sx2 - sx ** 2 + 1e-9)
        trend_pct = slope / (season_avg + 1e-9)

        if trend_pct > 0.10:
            trend = "HOT"
            reasoning.append(f"On a hot streak — last 5 avg {recent_avg:.1f} vs season {season_avg:.1f}")
        elif trend_pct < -0.10:
            trend = "COLD"
            reasoning.append(f"Cold spell — last 5 avg {recent_avg:.1f} vs season {season_avg:.1f}")
        else:
            trend = "NEUTRAL"
    else:
        trend = "NEUTRAL"
        slope = 0.0

    # ── Location split ───────────────────────────────────────────────────────
    location_avg = (home_avg if is_home else away_avg) or season_avg
    location_label = "home" if is_home else "away"
    if abs(location_avg - season_avg) > season_avg * 0.05:
        diff = location_avg - season_avg
        reasoning.append(f"Player averages {abs(diff):.1f} {'more' if diff > 0 else 'less'} {location_label}")

    # ── Matchup adjustment ────────────────────────────────────────────────────
    # opp_def_rating: percentile rank (0=worst defense, 100=best defense)
    # 50th percentile = 0% adjustment; 0th = +10%; 100th = -10%
    matchup_adj_pct = (50 - opp_def_rating) / 50 * 0.10  # max ±10%
    matchup_adj = season_avg * matchup_adj_pct

    if opp_def_rating <= 25:
        matchup_grade = "A"
        reasoning.append("Excellent matchup — facing bottom-quartile defense")
    elif opp_def_rating <= 45:
        matchup_grade = "B"
        reasoning.append("Good matchup — below-average defense")
    elif opp_def_rating <= 65:
        matchup_grade = "C"
    elif opp_def_rating <= 80:
        matchup_grade = "D"
        reasoning.append("Tough matchup — above-average defense")
    else:
        matchup_grade = "F"
        reasoning.append("Very tough matchup — elite defense")

    # ── Pace / usage adjustment ───────────────────────────────────────────────
    # pace_factor > 1 = faster game = more possessions = more opportunities
    pace_adj = season_avg * (pace_factor - 1.0) * 0.5

    # Usage rate adjustment
    usage_ratio = usage_current / max(usage_season, 1.0)
    usage_adj = season_avg * (usage_ratio - 1.0) * 0.30
    if usage_ratio > 1.10:
        reasoning.append(f"Elevated usage ({usage_current:.0f}% vs season avg {usage_season:.0f}%)")
    elif usage_ratio < 0.90:
        reasoning.append(f"Reduced usage ({usage_current:.0f}% vs season avg {usage_season:.0f}%)")

    # Minutes projection adjustment
    if minutes_projection and minutes_season_avg > 0:
        min_ratio = minutes_projection / minutes_season_avg
        minutes_adj = season_avg * (min_ratio - 1.0) * 0.60
        if abs(min_ratio - 1.0) > 0.10:
            reasoning.append(
                f"Minutes projection {minutes_projection:.0f} vs season avg {minutes_season_avg:.0f}"
            )
    else:
        minutes_adj = 0.0

    # ── Weighted blend ────────────────────────────────────────────────────────
    recent_component = recent_avg * 0.40
    season_component = season_avg * 0.25
    location_component = location_avg * 0.15
    adj_component = (season_avg + matchup_adj + pace_adj + usage_adj + minutes_adj) * 0.20

    raw_projection = recent_component + season_component + location_component + adj_component

    # Apply injury reduction
    if injury_reduction > 0:
        raw_projection *= (1 - injury_reduction)
        reasoning.append(f"Injury risk applied: -{injury_reduction*100:.0f}% reduction")

    projected_value = max(0.0, round(raw_projection, 2))

    # ── Floor / Ceiling calculation ───────────────────────────────────────────
    all_vals = last_10 or last_5 or [season_avg]
    std_dev = _std_dev(all_vals) if len(all_vals) >= 3 else projected_value * 0.25
    floor = max(0.0, round(projected_value - 1.5 * std_dev, 2))
    ceiling = round(projected_value + 1.5 * std_dev, 2)
    volatility = round(min(std_dev / max(projected_value, 1.0), 1.0), 3)

    # ── Confidence score ──────────────────────────────────────────────────────
    samples = len(last_10 or last_5)
    data_confidence = min(samples / 15 * 40, 40)         # up to 40 pts for data volume
    consistency_score = max(0, 30 - volatility * 60)      # up to 30 pts for consistency
    matchup_score = {"A": 20, "B": 15, "C": 10, "D": 5, "F": 0}.get(matchup_grade, 10)
    trend_score = {"HOT": 10, "NEUTRAL": 5, "COLD": 0}.get(trend, 5)
    confidence = round(min(100, data_confidence + consistency_score + matchup_score + trend_score), 1)

    # ── Recommendation ────────────────────────────────────────────────────────
    # Compare projection to hypothetical line (caller passes line separately)
    components = {
        "recent_form": recent_component,
        "season_baseline": season_component,
        "location_split": location_component,
        "matchup_adjustment": matchup_adj,
        "pace_adjustment": pace_adj,
        "usage_adjustment": usage_adj,
        "minutes_adjustment": minutes_adj,
        "injury_reduction": -projected_value * injury_reduction if injury_reduction else 0,
    }

    recommendation = "NEUTRAL — need line to evaluate"

    return PlayerProjection(
        player_name="",           # caller fills this
        stat_type="",             # caller fills this
        projected_value=projected_value,
        floor=floor,
        ceiling=ceiling,
        confidence=confidence,
        volatility=volatility,
        components=components,
        trend=trend,
        matchup_grade=matchup_grade,
        recommendation=recommendation,
        reasoning=reasoning[:6],  # cap to 6 bullets
    )


def recommend_vs_line(projection: PlayerProjection, line: float) -> str:
    """Given a completed projection, compare to a prop line."""
    p = projection.projected_value
    edge = abs(p - line) / max(line, 1.0)

    if p > line:
        if edge > 0.12 and projection.confidence >= 65:
            return "STRONG OVER"
        if edge > 0.06:
            return "LEAN OVER"
        return "SLIGHT OVER"
    elif p < line:
        if edge > 0.12 and projection.confidence >= 65:
            return "STRONG UNDER"
        if edge > 0.06:
            return "LEAN UNDER"
        return "SLIGHT UNDER"
    return "PASS — projection at line"


def _std_dev(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance)
