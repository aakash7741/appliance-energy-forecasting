from __future__ import annotations

import numpy as np
import pandas as pd


def forecast(history: pd.Series, horizon: int, method: str) -> np.ndarray:
    y = history.to_numpy(dtype=float)
    if method == "Mean":
        return np.repeat(y.mean(), horizon)
    if method == "Naive":
        return np.repeat(y[-1], horizon)
    if method == "Daily seasonal naive":
        return np.resize(y[-24:], horizon)
    if method == "Weekly seasonal naive":
        return np.resize(y[-168:], horizon)
    if method == "Drift":
        steps = np.arange(1, horizon + 1)
        return y[-1] + steps * (y[-1] - y[0]) / (len(y) - 1)
    raise ValueError(f"Unknown benchmark: {method}")


def rolling_forecasts(series: pd.Series, train_end: int, horizon: int = 24) -> pd.DataFrame:
    methods = ["Mean", "Naive", "Daily seasonal naive", "Weekly seasonal naive", "Drift"]
    pieces = []
    for origin in range(train_end, len(series), horizon):
        steps = min(horizon, len(series) - origin)
        index = series.index[origin : origin + steps]
        history = series.iloc[:origin]
        part = pd.DataFrame(index=index)
        for method in methods:
            part[method] = forecast(history, steps, method)
        pieces.append(part)
    return pd.concat(pieces)

