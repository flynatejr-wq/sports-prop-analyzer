"""
Kelly Criterion bankroll sizing and related utilities.
All functions are pure — no side effects.
"""
from typing import Optional


def kelly_fraction(
    prob_win: float,
    decimal_odds: float,
    fraction: float = 0.25,
) -> float:
    """
    Full Kelly: f = (b*p - q) / b
    where b = net decimal odds - 1, p = win probability, q = 1 - p.
    fraction: multiplier for fractional Kelly (0.25 = quarter Kelly, recommended).
    Returns fraction of bankroll to bet, or 0 if negative.
    """
    b = decimal_odds - 1
    if b <= 0:
        return 0.0
    q = 1 - prob_win
    f = (b * prob_win - q) / b
    return max(0.0, round(f * fraction, 4))


def kelly_from_american(
    prob_win: float,
    american_odds: float,
    fraction: float = 0.25,
) -> float:
    """Kelly sizing from American odds."""
    if american_odds > 0:
        decimal = (american_odds / 100) + 1
    else:
        decimal = (100 / abs(american_odds)) + 1
    return kelly_fraction(prob_win, decimal, fraction)


def recommended_stake(
    bankroll: float,
    prob_win: float,
    american_odds: float,
    max_pct: float = 0.05,
    fraction: float = 0.25,
) -> float:
    """
    Recommended stake in dollars.
    Caps at max_pct of bankroll to prevent ruin.
    """
    kelly = kelly_from_american(prob_win, american_odds, fraction)
    capped = min(kelly, max_pct)
    return round(bankroll * capped, 2)


def expected_profit(stake: float, prob_win: float, decimal_odds: float) -> float:
    """Expected profit = stake * (prob_win * (decimal_odds - 1) - prob_loss * 1)."""
    return round(stake * (prob_win * (decimal_odds - 1) - (1 - prob_win)), 2)


def parlay_probability(individual_probs: list) -> float:
    """True probability of hitting all legs of a parlay."""
    result = 1.0
    for p in individual_probs:
        result *= p
    return round(result, 6)


def parlay_ev(individual_probs: list, parlay_payout: float) -> float:
    """
    EV of a parlay bet.
    parlay_payout: decimal payout (e.g. 6x for a 3-leg PrizePicks).
    Returns EV as a fraction of stake.
    """
    p_win = parlay_probability(individual_probs)
    return round((p_win * parlay_payout) - 1, 4)


def clv_tracking(
    line_at_bet: float,
    closing_line: float,
    direction: str = "over",
) -> float:
    """
    Closing Line Value: measures if you beat the closing line.
    Positive CLV = you got a better number than closing.
    direction: 'over' or 'under'
    """
    if direction == "over":
        # Lower line = better for over
        return round(closing_line - line_at_bet, 2)
    else:
        # Higher line = better for under
        return round(line_at_bet - closing_line, 2)


def roi(total_profit: float, total_staked: float) -> float:
    """Return on investment as a percentage."""
    if total_staked <= 0:
        return 0.0
    return round((total_profit / total_staked) * 100, 2)


def flat_stake_simulation(
    hit_rates: list,
    stake_per_bet: float = 1.0,
) -> dict:
    """
    Simulate flat-stake betting outcomes.
    hit_rates: list of (prob_win, payout_decimal) tuples.
    Returns summary stats.
    """
    wins = 0
    total_profit = 0.0
    total_staked = len(hit_rates) * stake_per_bet

    for prob_win, payout in hit_rates:
        import random
        won = random.random() < prob_win
        if won:
            wins += 1
            total_profit += stake_per_bet * (payout - 1)
        else:
            total_profit -= stake_per_bet

    return {
        "total_bets": len(hit_rates),
        "wins": wins,
        "losses": len(hit_rates) - wins,
        "hit_rate": round(wins / len(hit_rates) * 100, 1) if hit_rates else 0,
        "total_profit": round(total_profit, 2),
        "total_staked": round(total_staked, 2),
        "roi": roi(total_profit, total_staked),
    }
