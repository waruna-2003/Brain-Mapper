"""Standardized Knowledge Tracing evaluation metrics (AUC, Accuracy, RMSE)."""

from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import accuracy_score, roc_auc_score


def compute_kt_metrics(y_true: np.ndarray, y_prob: np.ndarray) -> dict[str, float]:
    """Compute AUC, Accuracy (@0.5), and RMSE over flat binary predictions."""
    y_true_arr = np.asarray(y_true, dtype=np.float64).ravel()
    y_prob_arr = np.asarray(y_prob, dtype=np.float64).ravel()

    if len(y_true_arr) == 0:
        return {"auc": float("nan"), "accuracy": float("nan"), "rmse": float("nan"), "count": 0}

    y_pred_bin = (y_prob_arr >= 0.5).astype(np.int64)
    acc = float(accuracy_score(y_true_arr.astype(np.int64), y_pred_bin))
    rmse = float(math.sqrt(float(np.mean((y_prob_arr - y_true_arr) ** 2))))

    if len(np.unique(y_true_arr)) < 2:
        auc = float("nan")
    else:
        auc = float(roc_auc_score(y_true_arr, y_prob_arr))

    return {
        "auc": auc,
        "accuracy": acc,
        "rmse": rmse,
        "count": int(len(y_true_arr)),
    }
