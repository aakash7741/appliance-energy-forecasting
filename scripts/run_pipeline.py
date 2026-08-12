#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".analysis_packages"))
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("HF_HOME", str(ROOT / ".cache/huggingface"))

import numpy as np
import pandas as pd

# Import pandas before statsmodels so its public decorator shim is initialized
# consistently across pandas 2.x installations.
from statsmodels.stats.diagnostic import acorr_ljungbox

from energy_forecasting.baselines import rolling_forecasts
from energy_forecasting.config import SETTINGS
from energy_forecasting.data import download_data, load_raw, resample_hourly, sha256, validate_and_save
from energy_forecasting.features import add_features, sarimax_exog
from energy_forecasting.foundation import chronos_rolling
from energy_forecasting.metrics import accuracy, interval_coverage
from energy_forecasting.ml_model import fit_hgb, permutation_table, rolling_recursive_hgb
from energy_forecasting.plots import (
    save_components, save_eda, save_forecasts, save_importance,
    save_metric_comparison, save_residual_diagnostics,
)
from energy_forecasting.sarimax_model import exhaustive_aic_search, fit_sarimax, rolling_sarimax
from energy_forecasting.stationarity import stationarity_table


def main():
    for directory in (SETTINGS.figures_dir, SETTINGS.tables_dir, SETTINGS.hourly_path.parent):
        directory.mkdir(parents=True, exist_ok=True)
    started = time.time()
    raw_path = download_data()
    raw = load_raw(raw_path)
    hourly = resample_hourly(raw)
    quality = validate_and_save(raw, hourly)
    quality["raw_sha256"] = sha256(raw_path)
    quality["hourly_target_mean_Wh"] = float(hourly["Appliances"].mean())
    quality["hourly_target_std_Wh"] = float(hourly["Appliances"].std())
    quality["hourly_target_min_Wh"] = float(hourly["Appliances"].min())
    quality["hourly_target_max_Wh"] = float(hourly["Appliances"].max())
    (ROOT / "outputs/data_quality.json").write_text(json.dumps(quality, indent=2))

    save_eda(hourly, SETTINGS.figures_dir / "01_eda_overview.png")
    save_components(hourly["Appliances"], SETTINGS.figures_dir / "02_components_acf.png")
    stationarity = stationarity_table(hourly["Appliances"])
    stationarity.to_csv(SETTINGS.tables_dir / "stationarity_tests.csv", index=False)

    y = hourly["Appliances"]
    train_end = len(y) - SETTINGS.test_hours
    train = y.iloc[:train_end]
    test = y.iloc[train_end:]
    split = {
        "target": "Appliances (hourly sum of six 10-minute Wh readings)",
        "horizon_hours": SETTINGS.horizon,
        "evaluation": "14 non-overlapping rolling origins, each 24 hours",
        "train_rows": train_end,
        "test_rows": len(test),
        "train_start": train.index.min().isoformat(),
        "train_end": train.index.max().isoformat(),
        "test_start": test.index.min().isoformat(),
        "test_end": test.index.max().isoformat(),
    }
    (ROOT / "outputs/problem_definition.json").write_text(json.dumps(split, indent=2))

    all_predictions = rolling_forecasts(y, train_end, SETTINGS.horizon)

    grid_path = SETTINGS.tables_dir / "sarima_aic_grid.csv"
    required_grid_size = 7 * 3 * 7  # 147: every p=0..6, d=0..2, q=0..6 combination
    if grid_path.exists() and len(pd.read_csv(grid_path)) == required_grid_size:
        grid = pd.read_csv(grid_path).sort_values("AIC", na_position="last")
    else:
        grid = exhaustive_aic_search(train, grid_path)
    reliable = grid[grid["converged"].astype(bool)].dropna(subset=["AIC"])
    best = reliable.iloc[0]
    order = (int(best.p), int(best.d), int(best.q))
    final_order = order

    sarimax_outputs = {}
    sarimax_results = {}
    for conditional, name in ((False, "SARIMAX calendar"), (True, "SARIMAX conditional")):
        exog = sarimax_exog(hourly, conditional)
        result = fit_sarimax(train, exog.iloc[:train_end], final_order)
        frame, state = rolling_sarimax(result, y, exog, train_end, SETTINGS.horizon)
        all_predictions[name] = frame["forecast"]
        sarimax_outputs[name] = frame
        sarimax_results[name] = result

    feature_frame = add_features(hourly)
    importance = None
    for mode, name in (("lag_time", "HGB lag+time"), ("weather", "HGB + weather (conditional)"), ("all", "HGB all covariates (conditional)")):
        model, columns = fit_hgb(feature_frame, train_end, mode)
        all_predictions[name] = rolling_recursive_hgb(model, hourly, train_end, mode, SETTINGS.horizon)
        if mode == "all":
            importance = permutation_table(model, feature_frame, columns, train_end)
            importance.to_csv(SETTINGS.tables_dir / "feature_importance.csv", index=False)
            save_importance(importance, SETTINGS.figures_dir / "06_feature_importance.png")

    chronos, chronos_status = chronos_rolling(y, train_end, SETTINGS.horizon)
    if chronos is not None:
        all_predictions["Chronos-T5 tiny zero-shot"] = chronos["forecast"]
    (ROOT / "outputs/foundation_status.json").write_text(json.dumps(chronos_status, indent=2))

    metrics_rows = []
    for name in all_predictions.columns:
        row = {"Model": name, **accuracy(test, all_predictions[name], train)}
        if name in sarimax_outputs:
            row["Interval"] = "95%"
            row["Coverage_pct"] = interval_coverage(test, sarimax_outputs[name]["lower_95"], sarimax_outputs[name]["upper_95"])
        elif name == "Chronos-T5 tiny zero-shot" and chronos is not None:
            row["Interval"] = "90%"
            row["Coverage_pct"] = interval_coverage(test, chronos["lower_90"], chronos["upper_90"])
        else:
            row["Interval"] = ""
            row["Coverage_pct"] = np.nan
        metrics_rows.append(row)
    metrics = pd.DataFrame(metrics_rows).sort_values("RMSE")
    metrics.to_csv(SETTINGS.tables_dir / "model_metrics.csv", index=False)
    all_predictions.to_csv(SETTINGS.tables_dir / "rolling_forecasts.csv")
    save_metric_comparison(metrics, SETTINGS.figures_dir / "07_model_comparison.png")

    residuals = sarimax_results["SARIMAX conditional"].resid.iloc[200:]
    save_residual_diagnostics(residuals, SETTINGS.figures_dir / "05_sarimax_residuals.png")
    lb = acorr_ljungbox(residuals, lags=[24, 48], return_df=True)
    lb.to_csv(SETTINGS.tables_dir / "sarimax_ljung_box.csv")

    last_index = test.index[-SETTINGS.horizon:]
    display_names = list(all_predictions.columns)
    final_preds = all_predictions.loc[last_index, display_names]
    lower, upper = {}, {}
    for name, frame in sarimax_outputs.items():
        lower[name] = frame.loc[last_index, "lower_95"]
        upper[name] = frame.loc[last_index, "upper_95"]
    if chronos is not None:
        lower["Chronos-T5 tiny zero-shot"] = chronos.loc[last_index, "lower_90"]
        upper["Chronos-T5 tiny zero-shot"] = chronos.loc[last_index, "upper_90"]
    save_forecasts(test.loc[last_index], final_preds, SETTINGS.figures_dir / "04_final_forecasts.png", lower, upper)

    summary = {
        "aic_winner": {"order": order, "aic": float(best.AIC), "final_order": final_order, "screening_hours": 24 * 60},
        "best_model": metrics.iloc[0]["Model"],
        "best_rmse": float(metrics.iloc[0]["RMSE"]),
        "strongest_benchmark": metrics[metrics.Model.isin(["Naive", "Daily seasonal naive", "Weekly seasonal naive", "Drift"])].iloc[0]["Model"],
        "runtime_seconds": time.time() - started,
    }
    (ROOT / "outputs/run_summary.json").write_text(json.dumps(summary, indent=2))
    print(metrics.to_string(index=False))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
