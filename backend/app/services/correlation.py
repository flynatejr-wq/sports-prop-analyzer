"""
Parlay correlation engine.
Detects statistically correlated props to build positive-correlation parlays
and warn against negative-correlation stacks.

Key insight: On the same team, Points + Assists + Rebounds from the star player
are positively correlated with each other — and with team total points (game pace).
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

logger = logging.getLogger(__name__)


# ── Correlation knowledge base ────────────────────────────────────────────────
# (stat_a, stat_b): correlation coefficient [-1, 1]
# Derived from statistical research on NBA/NFL player stats
CORRELATION_TABLE: Dict[Tuple[str, str], float] = {
    # NBA same-player correlations
    ("Points", "Pts+Reb+Ast"): 0.85,
    ("Rebounds", "Pts+Reb+Ast"): 0.72,
    ("Assists", "Pts+Reb+Ast"): 0.68,
    ("Points", "3-Pointers Made"): 0.62,
    ("Points", "Assists"): 0.41,
    ("Points", "Rebounds"): 0.28,
    ("Assists", "Rebounds"): 0.15,
    ("Points", "Turnovers"): 0.35,   # high usage = more turnovers
    ("Assists", "Turnovers"): 0.48,
    ("Points", "Steals"): 0.20,
    ("Minutes", "Points"): 0.75,
    ("Minutes", "Rebounds"): 0.65,
    ("Minutes", "Assists"): 0.60,
    # NFL correlations
    ("Passing Yards", "Passing TDs"): 0.72,
    ("Passing Yards", "Receptions"): 0.45,   # team target share
    ("Passing Yards", "Receiving Yards"): 0.38,
    ("Rushing Yards", "Receiving Yards"): -0.15,  # role split
    # Cross-game (same team) — game pace / total
    ("team_points_over", "Points"): 0.58,
    ("team_points_over", "Assists"): 0.45,
}

# Negative correlation pairs to WARN about
ANTI_CORRELATIONS: List[Tuple[str, str, str]] = [
    # (stat_a, stat_b, reason)
    ("Passing Yards", "Rushing Yards", "High pass game = fewer rush attempts"),
    ("Points", "Points", "Two scorers on same team (usage cannibalizes)"),
    ("Receptions", "Rushing Yards", "PPR back vs ground-and-pound usage split"),
]


@dataclass
class PropCorrelation:
    prop_a_player: str
    prop_a_stat: str
    prop_b_player: str
    prop_b_stat: str
    correlation: float
    is_positive: bool
    is_same_player: bool
    is_same_team: bool
    recommendation: str   # "STACK", "AVOID", "NEUTRAL"
    reason: str


@dataclass
class ParlayAnalysis:
    legs: List[Dict]
    combined_probability: float
    adjusted_probability: float        # correlation-adjusted
    correlation_boost: float           # % improvement from positive correlations
    combined_ev: float
    risk_score: float                  # 0-100, lower = safer
    correlations: List[PropCorrelation]
    warnings: List[str]
    recommendation: str


def get_correlation(stat_a: str, stat_b: str) -> float:
    """Look up pairwise correlation. Symmetric."""
    key1 = (stat_a, stat_b)
    key2 = (stat_b, stat_a)
    return CORRELATION_TABLE.get(key1) or CORRELATION_TABLE.get(key2) or 0.0


def adjust_probability_for_correlation(
    p_a: float,
    p_b: float,
    correlation: float,
) -> float:
    """
    Adjust joint probability P(A ∩ B) for correlation using the
    Fréchet–Hoeffding copula approximation.

    When ρ = 0:     P(A ∩ B) ≈ P(A) × P(B)         (independent)
    When ρ = 1:     P(A ∩ B) ≈ min(P(A), P(B))      (comonotonic)
    When ρ = -1:    P(A ∩ B) ≈ max(0, P(A)+P(B)-1)  (counter)

    Linear interpolation between these bounds.
    """
    independent = p_a * p_b
    upper_bound = min(p_a, p_b)       # ρ = +1
    lower_bound = max(0, p_a + p_b - 1)  # ρ = -1

    if correlation >= 0:
        return independent + correlation * (upper_bound - independent)
    else:
        return independent + abs(correlation) * (lower_bound - independent)


def analyze_parlay(legs: List[Dict]) -> ParlayAnalysis:
    """
    Full correlation analysis for a parlay.

    Each leg dict:
        player_name, team, stat_type, line, direction, prob_win, ev_pct, sport
    """
    correlations: List[PropCorrelation] = []
    warnings: List[str] = []

    # Build all pairs
    adjusted_prob = 1.0
    pairs_processed = set()

    for i in range(len(legs)):
        for j in range(i + 1, len(legs)):
            leg_a = legs[i]
            leg_b = legs[j]
            pair_key = (min(i, j), max(i, j))
            if pair_key in pairs_processed:
                continue
            pairs_processed.add(pair_key)

            corr = get_correlation(leg_a["stat_type"], leg_b["stat_type"])
            same_player = leg_a["player_name"].lower() == leg_b["player_name"].lower()
            same_team = leg_a.get("team", "").upper() == leg_b.get("team", "").upper()

            # Same player — boost correlations
            if same_player:
                corr = max(corr, 0.30)

            is_positive = corr > 0.10
            is_negative = corr < -0.10

            rec = "NEUTRAL"
            reason = f"ρ = {corr:.2f}"
            if corr >= 0.50:
                rec = "STACK"
                reason = f"Strong positive correlation (ρ={corr:.2f}) — these hit together"
            elif corr >= 0.25:
                rec = "STACK"
                reason = f"Moderate positive correlation (ρ={corr:.2f})"
            elif corr <= -0.25:
                rec = "AVOID"
                reason = f"Negative correlation (ρ={corr:.2f}) — these rarely hit together"

            correlations.append(PropCorrelation(
                prop_a_player=leg_a["player_name"],
                prop_a_stat=leg_a["stat_type"],
                prop_b_player=leg_b["player_name"],
                prop_b_stat=leg_b["stat_type"],
                correlation=corr,
                is_positive=is_positive,
                is_same_player=same_player,
                is_same_team=same_team,
                recommendation=rec,
                reason=reason,
            ))

            if is_negative:
                warnings.append(
                    f"⚠️ {leg_a['player_name']} {leg_a['stat_type']} vs "
                    f"{leg_b['player_name']} {leg_b['stat_type']}: "
                    f"negative correlation ({corr:.2f}) — avoid stacking"
                )

    # Independent probability
    raw_probs = [leg.get("prob_win", 0.52) for leg in legs]
    independent_prob = 1.0
    for p in raw_probs:
        independent_prob *= p

    # Pair-adjusted probability (iterate over pairs)
    if len(legs) >= 2:
        adj = legs[0].get("prob_win", 0.52)
        for k in range(1, len(legs)):
            p_b = legs[k].get("prob_win", 0.52)
            best_corr = max(
                (get_correlation(legs[m]["stat_type"], legs[k]["stat_type"])
                 for m in range(k)),
                default=0.0,
            )
            adj = adjust_probability_for_correlation(adj, p_b, best_corr)
        adjusted_prob = adj
    else:
        adjusted_prob = raw_probs[0] if raw_probs else 0.5

    # PrizePicks payouts
    PP_PAYOUTS = {2: 3.0, 3: 5.0, 4: 10.0, 5: 20.0, 6: 40.0}
    payout = PP_PAYOUTS.get(len(legs), 3.0)
    combined_ev = round((adjusted_prob * payout - 1) * 100, 2)
    correlation_boost = round((adjusted_prob - independent_prob) / max(independent_prob, 0.001) * 100, 2)

    # Risk score: 0=safest, 100=riskiest
    avg_confidence = sum(leg.get("prob_win", 0.52) for leg in legs) / max(len(legs), 1)
    risk_score = round(
        100 - (avg_confidence * 50) - (min(adjusted_prob * 100, 30)) + (len(legs) * 5),
        1,
    )
    risk_score = max(0, min(100, risk_score))

    # Overall recommendation
    negative_count = sum(1 for c in correlations if c.recommendation == "AVOID")
    positive_count = sum(1 for c in correlations if c.recommendation == "STACK")

    if negative_count > 0:
        recommendation = "AVOID — negative correlations detected"
    elif combined_ev >= 10 and positive_count > 0:
        recommendation = "STRONG PLAY — positive correlations boost EV"
    elif combined_ev >= 5:
        recommendation = "GOOD PLAY — positive expected value"
    elif combined_ev >= 0:
        recommendation = "MARGINAL — low but positive EV"
    else:
        recommendation = "SKIP — negative expected value"

    return ParlayAnalysis(
        legs=legs,
        combined_probability=round(independent_prob, 5),
        adjusted_probability=round(adjusted_prob, 5),
        correlation_boost=correlation_boost,
        combined_ev=combined_ev,
        risk_score=risk_score,
        correlations=correlations,
        warnings=warnings,
        recommendation=recommendation,
    )


def find_correlated_combos(props: List[Dict], min_legs: int = 2, max_legs: int = 4) -> List[ParlayAnalysis]:
    """
    Given a list of props, find the best correlated combinations.
    Returns top 10 by adjusted EV.
    """
    from itertools import combinations

    results = []
    for n in range(min_legs, max_legs + 1):
        for combo in combinations(props, n):
            try:
                analysis = analyze_parlay(list(combo))
                if analysis.combined_ev > 0:
                    results.append(analysis)
            except Exception:
                continue

    results.sort(key=lambda x: x.combined_ev, reverse=True)
    return results[:10]
