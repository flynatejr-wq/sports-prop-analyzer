"""
Model training pipeline using XGBoost, LightGBM, and Random Forest.
Trains per-sport or per-stat-type models and saves them to disk.
"""
import logging
import os
import pickle
from typing import Dict, Optional, Tuple
import numpy as np

logger = logging.getLogger(__name__)

MODELS_DIR = os.environ.get("MODELS_DIR", "./models")
os.makedirs(MODELS_DIR, exist_ok=True)


def _get_model_path(model_name: str, sport: str, stat_type: str) -> str:
    safe_stat = stat_type.lower().replace(" ", "_").replace("-", "_")
    return os.path.join(MODELS_DIR, f"{model_name}_{sport.lower()}_{safe_stat}.pkl")


def train_xgboost(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: Optional[np.ndarray] = None,
    y_val: Optional[np.ndarray] = None,
) -> object:
    try:
        import xgboost as xgb
    except ImportError:
        raise RuntimeError("xgboost not installed — run: pip install xgboost")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="logloss",
        random_state=42,
        verbosity=0,
    )

    eval_set = [(X_val, y_val)] if X_val is not None else None
    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        early_stopping_rounds=20 if eval_set else None,
        verbose=False,
    )
    return model


def train_lightgbm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: Optional[np.ndarray] = None,
    y_val: Optional[np.ndarray] = None,
) -> object:
    try:
        import lightgbm as lgb
    except ImportError:
        raise RuntimeError("lightgbm not installed — run: pip install lightgbm")

    callbacks = [lgb.early_stopping(20, verbose=False), lgb.log_evaluation(period=-1)]
    eval_set = [(X_val, y_val)] if X_val is not None else None

    model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.03,
        subsample=0.8,
        colsample_bytree=0.8,
        num_leaves=31,
        random_state=42,
        verbose=-1,
    )
    model.fit(
        X_train, y_train,
        eval_set=eval_set,
        callbacks=callbacks if eval_set else [lgb.log_evaluation(period=-1)],
    )
    return model


def train_random_forest(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> object:
    try:
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        raise RuntimeError("scikit-learn not installed")

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    return model


def train_ensemble(
    X: np.ndarray,
    y: np.ndarray,
    sport: str,
    stat_type: str,
    val_split: float = 0.15,
) -> Dict[str, float]:
    """
    Train all three models and save them. Returns validation metrics.
    """
    if len(X) < 30:
        logger.warning("Not enough samples to train (%d) for %s/%s", len(X), sport, stat_type)
        return {}

    # Train/val split
    split = max(1, int(len(X) * (1 - val_split)))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    metrics: Dict[str, float] = {}

    for model_name, train_fn in [
        ("xgboost", lambda: train_xgboost(X_train, y_train, X_val, y_val)),
        ("lightgbm", lambda: train_lightgbm(X_train, y_train, X_val, y_val)),
        ("random_forest", lambda: train_random_forest(X_train, y_train)),
    ]:
        try:
            model = train_fn()
            path = _get_model_path(model_name, sport, stat_type)
            with open(path, "wb") as f:
                pickle.dump(model, f)

            if len(X_val) > 0:
                preds = model.predict(X_val)
                acc = float(np.mean(preds == y_val))
                metrics[f"{model_name}_val_acc"] = round(acc, 4)
                logger.info("Trained %s for %s/%s — val_acc=%.3f", model_name, sport, stat_type, acc)
            else:
                logger.info("Trained %s for %s/%s (no val set)", model_name, sport, stat_type)
        except Exception as exc:
            logger.warning("Training failed for %s/%s/%s: %s", model_name, sport, stat_type, exc)

    return metrics


def load_model(model_name: str, sport: str, stat_type: str) -> Optional[object]:
    path = _get_model_path(model_name, sport, stat_type)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as exc:
        logger.error("Model load failed %s: %s", path, exc)
        return None
