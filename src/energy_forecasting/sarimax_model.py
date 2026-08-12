from __future__ import annotations

import itertools
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX


def exhaustive_aic_search(
    series: pd.Series,
    output: Path,
    p_values=range(7),
    d_values=range(3),
    q_values=range(7),
    max_hours: int = 24 * 60,
) -> pd.DataFrame:
    """Fit every required p,d,q combination on a recent fixed screening window."""
    search_y = series.iloc[-max_hours:].astype(float)
    rows = []
    for p, d, q in itertools.product(p_values, d_values, q_values):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                result = ARIMA(
                    search_y,
                    order=(p, d, q),
                    trend="n" if d else "c",
                    enforce_stationarity=False,
                    enforce_invertibility=False,
                ).fit(method_kwargs={"maxiter": 35})
            rows.append({"p": p, "d": d, "q": q, "AIC": result.aic, "converged": bool(result.mle_retvals.get("converged", True))})
        except Exception as exc:
            rows.append({"p": p, "d": d, "q": q, "AIC": np.nan, "converged": False, "error": type(exc).__name__})
        pd.DataFrame(rows).to_csv(output, index=False)
    return pd.DataFrame(rows).sort_values("AIC", na_position="last")


def fit_sarimax(y: pd.Series, exog: pd.DataFrame, order: tuple[int, int, int]):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = SARIMAX(
            y.astype(float),
            exog=exog,
            order=order,
            seasonal_order=(1, 0, 1, 24),
            trend="c" if order[1] == 0 else "n",
            enforce_stationarity=False,
            enforce_invertibility=False,
            simple_differencing=False,
        )
        return model.fit(disp=False, maxiter=120)


def rolling_sarimax(result, y_all: pd.Series, exog_all: pd.DataFrame, train_end: int, horizon: int = 24):
    state = result
    forecasts, lowers, uppers = [], [], []
    for origin in range(train_end, len(y_all), horizon):
        steps = min(horizon, len(y_all) - origin)
        future_x = exog_all.iloc[origin : origin + steps]
        pred = state.get_forecast(steps=steps, exog=future_x)
        ci = pred.conf_int(alpha=0.05)
        forecasts.extend(np.maximum(pred.predicted_mean.to_numpy(), 0))
        lowers.extend(np.maximum(ci.iloc[:, 0].to_numpy(), 0))
        uppers.extend(np.maximum(ci.iloc[:, 1].to_numpy(), 0))
        observed = y_all.iloc[origin : origin + steps]
        state = state.append(observed, exog=future_x, refit=False)
    index = y_all.index[train_end:]
    return pd.DataFrame({"forecast": forecasts, "lower_95": lowers, "upper_95": uppers}, index=index), state

