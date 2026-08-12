from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.tsa.seasonal import STL


COLORS = {"navy": "#17324D", "blue": "#2D6CDF", "cyan": "#1BA3A3", "orange": "#E67E22", "red": "#C94C4C", "gray": "#667085"}


def setup_style():
    sns.set_theme(style="whitegrid", context="paper")
    plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 220, "font.family": "DejaVu Sans", "axes.titleweight": "bold"})


def concise_dates(ax, minticks=3, maxticks=6):
    locator = mdates.AutoDateLocator(minticks=minticks, maxticks=maxticks)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))


def save_eda(hourly: pd.DataFrame, path: Path):
    setup_style()
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.8))
    y = hourly["Appliances"]
    axes[0, 0].plot(y.index, y, lw=0.45, color=COLORS["blue"], alpha=0.65)
    axes[0, 0].plot(y.rolling(168, center=True).mean(), lw=1.3, color=COLORS["orange"], label="7-day moving mean")
    axes[0, 0].set(title="Hourly appliance energy", ylabel="Wh per hour")
    concise_dates(axes[0, 0])
    axes[0, 0].legend(frameon=False)
    last = y.iloc[-24 * 14 :]
    axes[0, 1].plot(last.index, last, color=COLORS["navy"], lw=0.9)
    axes[0, 1].set(title="Final 14 days", ylabel="Wh per hour")
    concise_dates(axes[0, 1])
    profile = y.groupby(y.index.hour).agg(["mean", "median"])
    axes[1, 0].plot(profile.index, profile["mean"], marker="o", ms=3, label="Mean", color=COLORS["orange"])
    axes[1, 0].plot(profile.index, profile["median"], marker="o", ms=3, label="Median", color=COLORS["blue"])
    axes[1, 0].set(title="Within-day seasonal profile", xlabel="Hour of day", ylabel="Wh per hour", xticks=range(0, 24, 3))
    axes[1, 0].legend(frameon=False)
    dow = y.groupby(y.index.day_name()).mean().reindex(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
    axes[1, 1].bar(range(7), dow, color=COLORS["cyan"])
    axes[1, 1].set(title="Mean by day of week", ylabel="Wh per hour", xticks=range(7), xticklabels=[d[:3] for d in dow.index])
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def save_components(y: pd.Series, path: Path):
    setup_style()
    stl = STL(y, period=24, robust=True).fit()
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.8))
    axes[0, 0].plot(stl.observed.index, stl.observed, lw=0.4, color=COLORS["navy"])
    axes[0, 0].set(title="Observed")
    concise_dates(axes[0, 0])
    axes[0, 1].plot(stl.trend.index, stl.trend, lw=0.8, color=COLORS["orange"])
    axes[0, 1].set(title="STL trend")
    concise_dates(axes[0, 1])
    axes[1, 0].plot(stl.seasonal.index[-336:], stl.seasonal.iloc[-336:], lw=0.8, color=COLORS["cyan"])
    axes[1, 0].set(title="Daily seasonal component (last 14 days)")
    concise_dates(axes[1, 0])
    plot_acf(y, lags=24 * 8, ax=axes[1, 1], zero=False, color=COLORS["blue"])
    axes[1, 1].set(title="Autocorrelation (daily/weekly lags)", xlabel="Lag (hours)")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def save_forecasts(actual: pd.Series, predictions: pd.DataFrame, path: Path, lower=None, upper=None):
    setup_style()
    methods = list(predictions.columns)
    ncols = 2
    nrows = int(np.ceil(len(methods) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.35 * nrows), sharex=True, sharey=True)
    axes = np.atleast_1d(axes).ravel()
    for ax, method in zip(axes, methods):
        ax.plot(actual.index, actual, color="black", lw=1.4, label="Actual")
        ax.plot(predictions.index, predictions[method], color=COLORS["blue"], lw=1.25, label="Forecast")
        if lower is not None and method in lower:
            ax.fill_between(predictions.index, lower[method], upper[method], color=COLORS["blue"], alpha=0.16, label="Interval")
        ax.set_title(method)
        ax.set_ylabel("Wh")
    for ax in axes[len(methods):]:
        ax.remove()
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.975), ncol=3, frameon=False)
    fig.suptitle("Final rolling origin: 24-hour forecasts", y=0.997, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.945))
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def save_metric_comparison(metrics: pd.DataFrame, path: Path):
    setup_style()
    ordered = metrics.sort_values("RMSE")
    colors = [COLORS["orange"] if "seasonal naive" in model.lower() else COLORS["blue"] for model in ordered["Model"]]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].barh(ordered["Model"], ordered["RMSE"], color=colors)
    axes[0].invert_yaxis(); axes[0].set(title="RMSE (lower is better)", xlabel="Wh")
    axes[1].barh(ordered["Model"], ordered["MASE"], color=colors)
    axes[1].axvline(1, color=COLORS["red"], ls="--", lw=1, label="Daily-naive scale")
    axes[1].invert_yaxis(); axes[1].set(title="MASE", xlabel="Scaled absolute error")
    axes[1].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def save_residual_diagnostics(residuals: pd.Series, path: Path):
    setup_style()
    residuals = pd.Series(residuals).dropna()
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.5))
    axes[0].plot(residuals.index, residuals, lw=0.55, color=COLORS["navy"]); axes[0].axhline(0, color="black", lw=0.8)
    axes[0].set(title="SARIMAX residuals", ylabel="Wh")
    concise_dates(axes[0])
    plot_acf(residuals, lags=72, zero=False, ax=axes[1], color=COLORS["blue"]); axes[1].set(title="Residual ACF")
    stats.probplot(residuals, dist="norm", plot=axes[2]); axes[2].set(title="Normal Q-Q")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)


def save_importance(table: pd.DataFrame, path: Path):
    setup_style()
    top = table.head(15).sort_values("importance")
    fig, ax = plt.subplots(figsize=(7.3, 4.5))
    ax.barh(top["feature"], top["importance"], color=COLORS["cyan"])
    ax.set(title="Conditional HGB permutation importance", xlabel="Increase in log-MAE after permutation")
    fig.tight_layout(); fig.savefig(path, bbox_inches="tight"); plt.close(fig)
