"""
ML prediction interface — loads trained models and produces
confidence scores, projected stat lines, and risk classifications.
"""
import logging
from typing import Dict, List, Optional

import numpy as np

from app.ml.feature_engineering import build_features_for_prop
from app.ml.model_trainer import load_model

logger = logging.getLogger(__name__)

MODEL_NAMES = ["xgboost", "lightgbm", "random_forest"]


def predict_prop(
    player_stats: List[Dict],
    stat_type: str,
    prop_line: float,
    sport: str,
    is_home: bool = True,
    matchup_def_rating: float = 111.5,
    usage_rate: Optional[float] = None,
) -> Dict:
    """
    Run ensemble prediction for a single prop.

    Returns:
        confidence_over: probability [0,1] that the over hits
        confidence_under: probability [0,1] that the under hits
        projected_value: point estimate for the stat
        risk_level: LOW / MEDIUM / HIGH
        volatility_score: float 0-1
        model_agreement: how much models agree (1 = unanimous)
    """
    features = build_features_for_prop(
        player_stats=player_stats,
        target_stat=stat_type,
        prop_line=prop_line,
        matchup_def_rating=matchup_def_rating,
        is_home=is_home,
        usage_rate=usage_rate,
    )

    if features is None:
        return _fallback_prediction(player_stats, stat_type, prop_line)

    X = features.reshape(1, -1)
    prob_overs: List[float] = []
    loaded_count = 0

    for model_name in MODEL_NAMES:
        model = load_model(model_name, sport, stat_type)
        if model is None:
            continue
        try:
            prob = model.predict_proba(X)[0][1]  # probability of class=1 (over)
            prob_overs.append(float(prob))
            loaded_count += 1
        except Exception as exc:
            logger.warning("Predict failed for %s/%s/%s: %s", model_name, sport, stat_type, exc)

    if not prob_overs:
        return _fallback_prediction(player_stats, stat_type, prop_line)

    # Ensemble: simple average across models
    confidence_over = float(np.mean(prob_overs))
    confidence_under = 1.0 - confidence_over

    # Model agreement: 1 if all models agree directionally, lower if split
    if len(prob_overs) > 1:
        over_votes = sum(1 for p in prob_overs if p > 0.5)
        agreement = max(over_votes, len(prob_overs) - over_votes) / len(prob_overs)
    else:
        agreement = 1.0

    # Projected value: use feature avg_last_5 and season_avg blend
    # Feature indices: avg_last_5=0, season_avg=2
    projected = float(features[0] * 0.6 + features[2] * 0.4)

    # Volatility from feature index 12
    volatility = float(features[12])

    # Risk classification
    risk_level = _classify_risk(confidence_over, volatility, agreement)

    return {
        "confidence_over": round(confidence_over, 4),
        "confidence_under": round(confidence_under, 4),
        "projected_value": round(projected, 2),
        "risk_level": risk_level,
        "volatility_score": round(min(volatility, 1.0), 4),
        "model_agreement": round(agreement, 4),
        "models_used": loaded_count,
    }


def _classify_risk(confidence: float, volatility: float, agreement: float) -> str:
    """Classify risk as LOW, MEDIUM, or HIGH."""
    score = 0
    # Low confidence in either direction → higher risk
    if abs(confidence - 0.5) < 0.05:
        score += 2
    elif abs(confidence - 0.5) < 0.10:
        score += 1
    # High volatility
    if volatility > 0.4:
        score += 2
    elif volatility > 0.25:
        score += 1
    # Models disagree
    if agreement < 0.67:
        score += 1

    if score >= 3:
        return "HIGH"
    if score >= 1:
        return "MEDIUM"
    return "LOW"


def _fallback_prediction(
    player_stats: List[Dict],
    stat_type: str,
    prop_line: float,
) -> Dict:
    """Simple historical-average fallback when no model is available."""
    col = stat_type.lower().replace(" ", "_").replace("-", "_")
    values = [float(r[col]) for r in player_stats if r.get(col) is not None]

    if not values:
        return {
            "confidence_over": 0.5,
            "confidence_under": 0.5,
            "projected_value": prop_line,
            "risk_level": "HIGH",
            "volatility_score": 1.0,
            "model_agreement": 0.0,
            "models_used": 0,
        }

    avg = np.mean(values[:10])
    std = np.std(values[:10]) if len(values) >= 3 else avg * 0.25

    if std > 0:
        from scipy import stats as scipy_stats
        try:
            confidence_over = float(1 - scipy_stats.norm.cdf(prop_line, loc=avg, scale=std))
        except Exception:
            confidence_over = 0.5
    else:
        confidence_over = 1.0 if avg > prop_line else 0.0

    return {
        "confidence_over": round(confidence_over, 4),
        "confidence_under": round(1 - confidence_over, 4),
        "projected_value": round(float(avg), 2),
        "risk_level": "MEDIUM",
        "volatility_score": round(min(float(std) / (float(avg) + 1e-9), 1.0), 4),
        "model_agreement": 0.0,
        "models_used": 0,
    }
