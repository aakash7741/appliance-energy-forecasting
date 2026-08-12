from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.inspection import permutation_importance

from .features import INDOOR, LAGS, ROLLS, WEATHER, calendar_features, feature_columns


def fit_hgb(feature_frame: pd.DataFrame, train_end: int, mode: str):
    columns = feature_columns(mode)
    train = feature_frame.iloc[:train_end].dropna(subset=columns + ["Appliances"])
    model = HistGradientBoostingRegressor(
        learning_rate=0.055,
        max_iter=350,
        max_leaf_nodes=31,
        l2_regularization=1.0,
        min_samples_leaf=20,
        random_state=42,
    )
    model.fit(train[columns], np.log1p(train["Appliances"]))
    return model, columns


def _row_features(index, history: list[float], source_row: pd.Series, mode: str) -> pd.DataFrame:
    row = calendar_features(pd.DatetimeIndex([index])).iloc[0].to_dict()
    for lag in LAGS:
        row[f"lag_{lag}"] = history[-lag]
    history_array = np.asarray(history, dtype=float)
    for window in ROLLS:
        values = history_array[-window:]
        row[f"roll_mean_{window}"] = values.mean()
        row[f"roll_std_{window}"] = values.std(ddof=1)
    if mode in ("weather", "all"):
        for name in WEATHER:
            row[name] = source_row[name]
    if mode == "all":
        for name in INDOOR:
            row[name] = source_row[name]
        row["lights"] = source_row["lights"]
    return pd.DataFrame([row], index=[index])[feature_columns(mode)]


def rolling_recursive_hgb(model, raw_frame: pd.DataFrame, train_end: int, mode: str, horizon: int = 24) -> pd.Series:
    predictions = []
    for origin in range(train_end, len(raw_frame), horizon):
        history = raw_frame["Appliances"].iloc[:origin].astype(float).tolist()
        steps = min(horizon, len(raw_frame) - origin)
        for step in range(steps):
            pos = origin + step
            x = _row_features(raw_frame.index[pos], history, raw_frame.iloc[pos], mode)
            prediction = max(float(np.expm1(model.predict(x)[0])), 0)
            predictions.append(prediction)
            history.append(prediction)
    return pd.Series(predictions, index=raw_frame.index[train_end:])


def permutation_table(model, feature_frame: pd.DataFrame, columns: list[str], test_start: int) -> pd.DataFrame:
    test = feature_frame.iloc[test_start:].dropna(subset=columns + ["Appliances"])
    result = permutation_importance(
        model,
        test[columns],
        np.log1p(test["Appliances"]),
        n_repeats=5,
        random_state=42,
        scoring="neg_mean_absolute_error",
    )
    table = pd.DataFrame({"feature": columns, "importance": result.importances_mean})
    return table.sort_values("importance", ascending=False)

