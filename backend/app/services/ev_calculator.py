"""
EV (Expected Value) calculation engine.

Core formulas:
  implied_prob(american_odds) → probability
  fair_value(line, historical_avg) → what the line SHOULD be
  ev(fair_prob, offered_prob) → edge %

All public methods are pure functions — no I/O, easy to unit test.
"""
from typing import Optional, Tuple
import math


def american_to_decimal(odds: float) -> float:
    """Convert American odds to decimal odds."""
    if odds > 0:
        return (odds / 100) + 1
    return (100 / abs(odds)) + 1


def american_to_implied_prob(odds: float) -> float:
    """
    Convert American odds to implied probability (includes vig).
    Returns probability in [0, 1].
    """
    if odds > 0:
        return 100 / (odds + 100)
    return abs(odds) / (abs(odds) + 100)


def remove_vig(over_odds: float, under_odds: float) -> Tuple[float, float]:
    """
    Remove sportsbook vig to get true (no-vig) probabilities.
    Returns (true_prob_over, true_prob_under) that sum to 1.0.
    """
    p_over = american_to_implied_prob(over_odds)
    p_under = american_to_implied_prob(under_odds)
    total = p_over + p_under
    if total <= 0:
        return 0.5, 0.5
    return p_over / total, p_under / total


def true_prob_to_american(prob: float) -> float:
    """Convert true probability back to American odds."""
    if prob <= 0 or prob >= 1:
        return 0.0
    if prob >= 0.5:
        return -round((prob / (1 - prob)) * 100, 1)
    return round(((1 - prob) / prob) * 100, 1)


def calculate_ev(fair_prob: float, payout_odds: float) -> float:
    """
    Calculate expected value as a percentage edge.
    fair_prob: your estimated true probability of winning
    payout_odds: American odds being offered
    Returns EV% (positive = +EV, e.g. 7.5 means 7.5% edge)
    """
    decimal = american_to_decimal(payout_odds)
    ev = (fair_prob * decimal) - 1
    return round(ev * 100, 2)


def prizepicks_ev(
    fair_prob: float,
    pp_line: float,
    direction: str = "over",
) -> float:
    """
    Calculate EV for PrizePicks (no juice, -110 equivalent implied at ~52.38%).
    PrizePicks pays 2x on single picks (implied -110 each side effectively).
    Fair payout on PrizePicks: if you win, profit = 1x stake.
    EV = fair_prob * 1 - (1 - fair_prob) * 1 = 2*fair_prob - 1
    Returned as a percentage.
    """
    ev = (fair_prob * 1.0) - ((1 - fair_prob) * 1.0)
    return round(ev * 100, 2)


def hit_rate_to_fair_prob(
    last_5: list,
    season_avg: float,
    line: float,
    home_avg: Optional[float] = None,
    away_avg: Optional[float] = None,
    is_home: bool = True,
    matchup_adjustment: float = 0.0,
) -> float:
    """
    Estimate true over probability for a prop line using historical data.
    Uses weighted combination of recent form and season average.
    matchup_adjustment: positive = easier matchup (increases over prob), in std-dev units.
    """
    # Recent form: what % of last N games went over the line
    if last_5:
        recent_hit_rate = sum(1 for g in last_5 if g > line) / len(last_5)
    else:
        recent_hit_rate = 0.5

    # Season-long hit rate estimate — use normal distribution approximation
    # Assume ~20% standard deviation around season average
    if season_avg > 0:
        std_dev = season_avg * 0.25
        if std_dev > 0:
            z = (line - season_avg) / std_dev
            season_hit_rate = 1 - _normal_cdf(z)
        else:
            season_hit_rate = 0.5 if season_avg == line else (1.0 if season_avg > line else 0.0)
    else:
        season_hit_rate = 0.5

    # Home/away split if available
    location_avg = home_avg if is_home else away_avg
    if location_avg and location_avg > 0:
        std_dev = location_avg * 0.25
        if std_dev > 0:
            z = (line - location_avg) / std_dev
            location_hit_rate = 1 - _normal_cdf(z)
        else:
            location_hit_rate = season_hit_rate
    else:
        location_hit_rate = season_hit_rate

    # Weighted blend: recent form 40%, season 40%, location 20%
    blended = (recent_hit_rate * 0.40) + (season_hit_rate * 0.40) + (location_hit_rate * 0.20)

    # Apply matchup adjustment (in %)
    adjusted = blended + (matchup_adjustment / 100)
    return max(0.01, min(0.99, adjusted))


def _normal_cdf(z: float) -> float:
    """Approximate standard normal CDF using Hart approximation."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def calculate_line_discrepancy(pp_line: float, consensus_line: float) -> float:
    """
    Positive = PP line is higher than market (harder to go over on PP).
    Negative = PP line is lower than market (easier to go over on PP → value on over).
    """
    return round(pp_line - consensus_line, 2)


def calculate_implied_prob_from_line(
    pp_line: float, season_avg: float, std_dev_pct: float = 0.25
) -> Tuple[float, float]:
    """
    Given a prop line and season average, estimate market-implied over/under probabilities.
    Returns (prob_over, prob_under).
    """
    if season_avg <= 0:
        return 0.5, 0.5
    std = season_avg * std_dev_pct
    if std <= 0:
        return 0.5, 0.5
    z = (pp_line - season_avg) / std
    prob_over = 1 - _normal_cdf(z)
    return round(prob_over, 4), round(1 - prob_over, 4)


def is_stale_line(
    line: float,
    consensus_line: float,
    threshold: float = 0.5,
) -> bool:
    """Line is stale if it hasn't moved with the market by more than threshold."""
    return abs(line - consensus_line) >= threshold


def classify_edge(ev_pct: float) -> str:
    """Classify an edge percentage into a tier."""
    if ev_pct >= 15:
        return "ELITE"
    if ev_pct >= 10:
        return "STRONG"
    if ev_pct >= 5:
        return "GOOD"
    if ev_pct >= 2:
        return "SLIGHT"
    if ev_pct >= 0:
        return "MARGINAL"
    return "NEGATIVE"


def detect_steam_move(
    line_history: list,
    current_line: float,
    window_minutes: int = 5,
) -> bool:
    """
    Detect steam move: rapid line movement in a short window.
    line_history: list of (timestamp, line) tuples sorted oldest → newest.
    """
    if len(line_history) < 2:
        return False
    recent = [l for ts, l in line_history if True]  # simplified — filter by time in production
    if not recent:
        return False
    movement = abs(current_line - recent[0])
    return movement >= 1.0  # 1+ unit move = steam indicator
