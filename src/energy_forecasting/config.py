from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    data_url: str = (
        "https://archive.ics.uci.edu/ml/machine-learning-databases/"
        "00374/energydata_complete.csv"
    )
    raw_path: Path = ROOT / "data/raw/energydata_complete.csv"
    hourly_path: Path = ROOT / "data/processed/energy_hourly.csv"
    figures_dir: Path = ROOT / "outputs/figures"
    tables_dir: Path = ROOT / "outputs/tables"
    horizon: int = 24
    test_hours: int = 14 * 24
    seasonal_period: int = 24
    weekly_period: int = 24 * 7
    random_state: int = 42


SETTINGS = Settings()

