# Appliance Energy Forecasting

A reproducible forecasting study of the [UCI Appliances Energy Prediction dataset](https://archive.ics.uci.edu/dataset/374/appliances+energy+prediction). The repository downloads the 10-minute data, aggregates energy to hourly Wh, performs EDA and stationarity testing, and compares simple benchmarks, SARIMAX, histogram gradient boosting (HGB), and Amazon Chronos-T5 over a 24-hour horizon.

## Main finding

The last 14 days are evaluated as 14 non-overlapping rolling origins, each with a 24-hour horizon. Weekly seasonal naive is the strongest benchmark (RMSE 474.70 Wh). The deployable calendar-only SARIMAX reaches 380.34 Wh RMSE (19.9% lower) and near-nominal 94.9% coverage for its 95% intervals. The conditional all-covariate HGB is numerically best at 378.17 Wh, only 0.6% better than SARIMAX, while relying on future sensor/weather observations. The practical recommendation is therefore calendar-only SARIMAX; use HGB when point MAE is paramount and every input can be supplied honestly at the forecast origin.

| Model | RMSE (Wh) | MAE (Wh) | MASE | Status |
|---|---:|---:|---:|---|
| HGB all covariates | 378.17 | 203.31 | 0.634 | Conditional |
| SARIMAX calendar | 380.34 | 216.10 | 0.674 | Deployable |
| HGB + weather | 380.88 | 203.20 | 0.634 | Conditional |
| HGB lag + time | 389.16 | 210.79 | 0.658 | Deployable |
| Chronos-T5 tiny | 460.51 | 227.51 | 0.710 | Zero-shot |
| Weekly seasonal naive | 474.70 | 254.58 | 0.794 | Benchmark |
| Daily seasonal naive | 510.70 | 288.57 | 0.900 | Benchmark |

The full table, including mean, naive, drift, conditional SARIMAX, bias, percentage errors, and interval coverage, is in `outputs/tables/model_metrics.csv`.

## Forecasting design

- **Target:** hourly `Appliances` energy in Wh. The six 10-minute Wh readings are summed; continuous sensor and weather variables are averaged.
- **Horizon:** 24 hours.
- **Initial training window:** 11 January to 13 May 2016 (2,954 hours).
- **Test window:** final 14 days (336 hours), evaluated using 14 daily rolling origins. Model parameters are held fixed while newly observed target history is released at each origin.
- **Metrics:** RMSE (primary), MAE, MAPE, sMAPE, MASE (daily seasonal scale), bias, and empirical interval coverage where available.
- **Leakage rule:** lag/rolling features are shifted by one hour and created separately at each rolling origin. Models marked *conditional* use realised future sensor/weather values and are not deployable forecasts unless equivalent covariate forecasts exist at prediction time.

## Repository layout

```text
.
├── data/                  # downloaded raw data and generated hourly data
├── notebooks/01_analysis.ipynb
├── outputs/
│   ├── figures/           # EDA, diagnostics, forecasts, importance, comparison
│   └── tables/            # metrics, forecasts, AIC grid, tests, diagnostics
├── report/                # eight-page report and report builder
├── scripts/
│   ├── bootstrap.sh       # isolated environment, including CPU Chronos stack
│   ├── run_pipeline.sh    # one-command analysis
│   └── run_pipeline.py
├── src/energy_forecasting # reusable data, feature, model, metric, plotting modules
└── tests/                 # fast unit tests for aggregation, lags, metrics, baselines
```

## Reproduce the analysis

Python 3.11 or 3.12 is recommended. From the repository root:

```bash
./scripts/bootstrap.sh
source .venv/bin/activate
./scripts/run_pipeline.sh
python -m pytest -q
```

The first run downloads approximately 11.4 MB of data and the public `amazon/chronos-t5-tiny` checkpoint. Chronos is optional: if its dependencies or checkpoint are unavailable, the pipeline completes the other models and writes the reason to `outputs/foundation_status.json` instead of substituting a proxy. The required AIC search checkpoints all 147 combinations (`p=0..6`, `d=0..2`, `q=0..6`) to `outputs/tables/sarima_aic_grid.csv`; delete or rename that table only when a fresh grid is wanted.

## Method notes

The AIC screen uses the most recent 60 training days to make the exhaustive search practical and retains only converged fits for order selection. The selected non-seasonal order is `(0,1,6)`. Both SARIMAX variants use daily seasonality `(1,0,1,24)`; the deployable version uses only calendar Fourier terms, while the conditional version adds realised kitchen/outdoor temperature, humidity, and wind speed. HGB uses lags 1, 2, 3, 24, 25, 48, 168; rolling means/standard deviations over 3, 24, 168 hours; calendar features; and, in conditional variants, weather/indoor sensors. Chronos-T5 is evaluated zero-shot with a 512-hour context, 40 sample paths, and median forecasts.

## Outputs and report

- [Eight-page report](report/appliance_energy_forecasting_report.pdf)
- [Editable report](report/appliance_energy_forecasting_report.docx)
- [Model metrics](outputs/tables/model_metrics.csv)
- [All rolling forecasts](outputs/tables/rolling_forecasts.csv)
- [AIC grid](outputs/tables/sarima_aic_grid.csv)
- [Stationarity tests](outputs/tables/stationarity_tests.csv)

## References

Candanedo, L. M., Feldheim, V., & Deramaix, D. (2017). Data driven prediction models of energy use of appliances in a low-energy house. *Energy and Buildings, 140*, 81–97. https://doi.org/10.1016/j.enbuild.2017.01.083

Ansari, A. F., et al. (2024). Chronos: Learning the language of time series. *Transactions on Machine Learning Research*. https://arxiv.org/abs/2403.07815

Hyndman, R. J., & Athanasopoulos, G. (2021). *Forecasting: Principles and Practice* (3rd ed.). OTexts. https://otexts.com/fpp3/

The dataset is CC BY 4.0. Repository code is provided under the MIT License.

