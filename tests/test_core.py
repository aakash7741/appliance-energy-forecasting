import numpy as np
import pandas as pd

from energy_forecasting.baselines import forecast
from energy_forecasting.data import resample_hourly
from energy_forecasting.features import add_features
from energy_forecasting.metrics import accuracy


def test_hourly_energy_is_summed_and_sensor_is_averaged():
    index = pd.date_range("2020-01-01", periods=12, freq="10min")
    raw = pd.DataFrame({"Appliances": 10.0, "lights": 1.0, "T1": np.arange(12)}, index=index)
    hourly = resample_hourly(raw)
    assert hourly.iloc[0]["Appliances"] == 60
    assert hourly.iloc[0]["lights"] == 6
    assert hourly.iloc[0]["T1"] == 2.5


def test_daily_seasonal_naive():
    y = pd.Series(np.arange(48.0))
    assert np.array_equal(forecast(y, 24, "Daily seasonal naive"), np.arange(24.0, 48.0))


def test_lags_use_only_the_past():
    index = pd.date_range("2020-01-01", periods=200, freq="h")
    frame = pd.DataFrame({"Appliances": np.arange(200.0)}, index=index)
    featured = add_features(frame)
    assert featured.iloc[24]["lag_24"] == 0
    assert featured.iloc[24]["roll_mean_24"] == np.mean(np.arange(24.0))


def test_zero_error_metrics():
    train = pd.Series(np.arange(50.0) + 1)
    result = accuracy([10, 20], [10, 20], train)
    assert result["RMSE"] == 0
    assert result["MAE"] == 0

