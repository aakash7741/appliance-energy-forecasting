from __future__ import annotations

import numpy as np
import pandas as pd


LAGS = (1, 2, 3, 24, 25, 48, 168)
ROLLS = (3, 24, 168)
WEATHER = ("T_out", "RH_out", "Press_mm_hg", "Windspeed", "Visibility", "Tdewpoint")
INDOOR = tuple([f"T{i}" for i in range(1, 10)] + [f"RH_{i}" for i in range(1, 10)])


def calendar_features(index: pd.DatetimeIndex) -> pd.DataFrame:
    hour = index.hour.to_numpy()
    dow = index.dayofweek.to_numpy()
    return pd.DataFrame(
        {
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "dow_sin": np.sin(2 * np.pi * dow / 7),
            "dow_cos": np.cos(2 * np.pi * dow / 7),
            "is_weekend": (dow >= 5).astype(int),
        },
        index=index,
    )


def add_features(frame: pd.DataFrame, target: str = "Appliances") -> pd.DataFrame:
    features = frame.copy()
    features = features.join(calendar_features(features.index))
    y = features[target]
    for lag in LAGS:
        features[f"lag_{lag}"] = y.shift(lag)
    shifted = y.shift(1)
    for window in ROLLS:
        features[f"roll_mean_{window}"] = shifted.rolling(window).mean()
        features[f"roll_std_{window}"] = shifted.rolling(window).std()
    return features


def feature_columns(mode: str = "all") -> list[str]:
    time = ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "is_weekend"]
    lags = [f"lag_{lag}" for lag in LAGS]
    rolls = [name for window in ROLLS for name in (f"roll_mean_{window}", f"roll_std_{window}")]
    if mode == "lag_time":
        return time + lags + rolls
    if mode == "weather":
        return time + lags + rolls + list(WEATHER)
    if mode == "all":
        return time + lags + rolls + list(WEATHER) + list(INDOOR) + ["lights"]
    raise ValueError(f"Unknown feature mode: {mode}")


def sarimax_exog(frame: pd.DataFrame, conditional: bool) -> pd.DataFrame:
    exog = calendar_features(frame.index)
    if conditional:
        chosen = ["T1", "RH_1", "T_out", "RH_out", "Windspeed"]
        exog = exog.join(frame[chosen])
    return exog.astype(float)

