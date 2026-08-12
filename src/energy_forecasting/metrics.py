from __future__ import annotations

import numpy as np
import pandas as pd


def accuracy(y_true, y_pred, train: pd.Series, seasonal_period: int = 24) -> dict[str, float]:
    actual = np.asarray(y_true, dtype=float)
    forecast = np.asarray(y_pred, dtype=float)
    error = actual - forecast
    scale = np.mean(np.abs(np.asarray(train[seasonal_period:]) - np.asarray(train[:-seasonal_period])))
    denom = np.abs(actual) + np.abs(forecast)
    return {
        "RMSE": float(np.sqrt(np.mean(error**2))),
        "MAE": float(np.mean(np.abs(error))),
        "MAPE_pct": float(np.mean(np.abs(error) / np.maximum(np.abs(actual), 1e-9)) * 100),
        "sMAPE_pct": float(np.mean(2 * np.abs(error) / np.maximum(denom, 1e-9)) * 100),
        "MASE": float(np.mean(np.abs(error)) / scale),
        "Bias": float(np.mean(forecast - actual)),
    }


def interval_coverage(y_true, lower, upper) -> float:
    actual = np.asarray(y_true)
    return float(np.mean((actual >= np.asarray(lower)) & (actual <= np.asarray(upper))) * 100)

