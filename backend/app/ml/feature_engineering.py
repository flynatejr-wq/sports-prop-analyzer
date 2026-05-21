"""
Feature engineering for prop prediction models.
Transforms raw PlayerStats rows into ML-ready feature vectors.
"""
import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Stat columns available in PlayerStats
STAT_COLUMNS = [
    "points", "rebounds", "assists", "steals", "blocks", "turnovers",
    "three_pointers", "minutes", "passing_yards", "passing_tds",
    "rushing_yards", "receiving_yards", "receptions",
    "hits", "strikeouts", "earned_runs", "shots_on_goal", "goals",
]


def build_features_for_prop(
    player_stats: List[Dict],
    target_stat: str,
    prop_line: float,
    matchup_def_rating: float = 111.5,
    is_home: bool = True,
    usage_rate: Optional[float] = None,
) -> Optional[np.ndarray]:
    """
    Build a feature vector for predicting whether a prop line goes over/under.

    Features:
    - Last 5 / 10 game averages for the target stat
    - Season average, home/away split
    - Trend (slope of last 5)
    - Hit rate over the line in last 10 games
    - Minutes consistency (std dev)
    - Usage rate
    - Matchup difficulty (opp def rating normalized)
    - Is home flag
    - Line relative to season average (z-score)

    Returns None if insufficient data.
    """
    if not player_stats or len(player_stats) < 3:
        return None

    col = target_stat.lower().replace(" ", "_").replace("-", "_")

    # Collect stat values (most recent first)
    values = []
    home_values = []
    away_values = []
    minutes_vals = []

    for row in player_stats:
        v = row.get(col)
        if v is not None:
            values.append(float(v))
            if row.get("is_home"):
                home_values.append(float(v))
            else:
                away_values.append(float(v))
        mins = row.get("minutes")
        if mins is not None:
            minutes_vals.append(float(mins))

    if not values:
        return None

    # Rolling averages
    avg_last_5 = np.mean(values[:5]) if len(values) >= 5 else np.mean(values)
    avg_last_10 = np.mean(values[:10]) if len(values) >= 10 else np.mean(values)
    season_avg = np.mean(values)

    # Home / away splits
    home_avg = np.mean(home_values) if home_values else season_avg
    away_avg = np.mean(away_values) if away_values else season_avg

    # Trend: slope of last 5 games (positive = improving)
    trend = 0.0
    if len(values) >= 5:
        recent = values[:5][::-1]  # oldest→newest
        x = np.arange(len(recent))
        try:
            slope = np.polyfit(x, recent, 1)[0]
            trend = float(slope)
        except Exception:
            pass

    # Hit rate over line in last 10
    hit_rate = sum(1 for v in values[:10] if v > prop_line) / min(len(values), 10)

    # Minutes consistency
    minutes_std = float(np.std(minutes_vals)) if len(minutes_vals) >= 3 else 0.0
    avg_minutes = float(np.mean(minutes_vals)) if minutes_vals else 0.0

    # Z-score of line vs season average
    std_dev = float(np.std(values)) if len(values) >= 3 else season_avg * 0.25
    if std_dev > 0:
        line_z_score = (prop_line - season_avg) / std_dev
    else:
        line_z_score = 0.0

    # Normalize matchup (relative to league avg 111.5)
    matchup_normalized = (matchup_def_rating - 111.5) / 5.0

    # Usage rate (default league average ~20%)
    usage = (usage_rate or 20.0) / 30.0  # normalize

    # Variance / consistency
    volatility = float(np.std(values[:10])) / (avg_last_10 + 1e-9) if avg_last_10 > 0 else 0.0

    features = np.array([
        avg_last_5,
        avg_last_10,
        season_avg,
        home_avg if is_home else away_avg,
        trend,
        hit_rate,
        line_z_score,
        matchup_normalized,
        float(is_home),
        avg_minutes,
        minutes_std,
        usage,
        volatility,
        prop_line,
        abs(prop_line - season_avg),             # distance from average
        min(len(values), 30) / 30.0,             # games played (normalized)
    ], dtype=np.float32)

    return features


def build_training_dataset(
    historical_props: List[Dict],
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Build X, y arrays for model training from historical prop records.
    Each prop must have: stat_type, line, actual_value, player_stats (list of dicts).
    y = 1 if actual_value > line (over hit), 0 otherwise.
    """
    X_rows = []
    y_rows = []

    for prop in historical_props:
        actual = prop.get("actual_value")
        line = prop.get("line")
        if actual is None or line is None:
            continue

        label = 1 if actual > line else 0
        player_stats = prop.get("player_stats", [])
        stat_type = prop.get("stat_type", "")

        features = build_features_for_prop(
            player_stats=player_stats,
            target_stat=stat_type,
            prop_line=line,
            matchup_def_rating=prop.get("opp_def_rating", 111.5),
            is_home=prop.get("is_home", True),
            usage_rate=prop.get("usage_rate"),
        )

        if features is not None:
            X_rows.append(features)
            y_rows.append(label)

    if not X_rows:
        return None, None

    return np.array(X_rows, dtype=np.float32), np.array(y_rows, dtype=np.int32)


FEATURE_NAMES = [
    "avg_last_5", "avg_last_10", "season_avg", "location_avg",
    "trend", "hit_rate", "line_z_score", "matchup_normalized",
    "is_home", "avg_minutes", "minutes_std", "usage", "volatility",
    "prop_line", "distance_from_avg", "games_played_norm",
]
