from __future__ import annotations

import warnings

import pandas as pd
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tools.sm_exceptions import InterpolationWarning


def stationarity_table(series: pd.Series) -> pd.DataFrame:
    variants = {
        "Level": series.dropna(),
        "First difference": series.diff().dropna(),
        "Daily difference": series.diff(24).dropna(),
        "First + daily difference": series.diff().diff(24).dropna(),
    }
    rows = []
    for name, values in variants.items():
        adf = adfuller(values, autolag="AIC")
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", InterpolationWarning)
                kp = kpss(values, regression="c", nlags="auto")
            kp_stat, kp_p = kp[0], kp[1]
        except ValueError:
            kp_stat, kp_p = float("nan"), float("nan")
        rows.append(
            {
                "Transformation": name,
                "ADF statistic": adf[0],
                "ADF p-value": adf[1],
                "KPSS statistic": kp_stat,
                "KPSS p-value": kp_p,
            }
        )
    return pd.DataFrame(rows)
