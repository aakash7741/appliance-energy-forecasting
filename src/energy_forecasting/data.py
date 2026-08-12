from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path

import pandas as pd

from .config import SETTINGS


ENERGY_COLUMNS = ["Appliances", "lights"]


def download_data(url: str = SETTINGS.data_url, path: Path = SETTINGS.raw_path) -> Path:
    """Download the UCI CSV only when it is not already present."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        urllib.request.urlretrieve(url, path)
    if path.stat().st_size < 10_000_000:
        raise ValueError(f"Downloaded file looks incomplete: {path}")
    return path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_raw(path: Path = SETTINGS.raw_path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"], skipinitialspace=True)
    frame = frame.sort_values("date").set_index("date")
    if not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
        raise ValueError("Timestamp index must be unique and increasing")
    return frame


def resample_hourly(frame: pd.DataFrame) -> pd.DataFrame:
    """Aggregate 10-minute Wh readings to hourly Wh; average sensors/weather."""
    aggregations = {column: "mean" for column in frame.columns}
    for column in ENERGY_COLUMNS:
        aggregations[column] = "sum"
    hourly = frame.resample("1h").agg(aggregations)
    hourly.index.name = "date"
    return hourly


def validate_and_save(raw: pd.DataFrame, hourly: pd.DataFrame) -> dict:
    expected = pd.date_range(raw.index.min(), raw.index.max(), freq="10min")
    expected_hourly = pd.date_range(hourly.index.min(), hourly.index.max(), freq="1h")
    quality = {
        "raw_rows": int(len(raw)),
        "raw_columns": int(raw.shape[1]),
        "raw_start": raw.index.min().isoformat(),
        "raw_end": raw.index.max().isoformat(),
        "raw_missing_cells": int(raw.isna().sum().sum()),
        "missing_timestamps_10min": int(len(expected.difference(raw.index))),
        "duplicate_timestamps": int(raw.index.duplicated().sum()),
        "hourly_rows": int(len(hourly)),
        "hourly_missing_cells": int(hourly.isna().sum().sum()),
        "missing_timestamps_hourly": int(len(expected_hourly.difference(hourly.index))),
    }
    SETTINGS.hourly_path.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(SETTINGS.hourly_path)
    return quality

