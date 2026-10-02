---
library_name: lightgbm
license: mit
language:
- en
pipeline_tag: tabular-regression
tags:
- energy
- solar
- pv-forecasting
- probabilistic-forecasting
- quantile-regression
- conformal-prediction
- gradient-boosting
- energy-community
- enertef
---

# Service 2 — localised PV generation forecasting (Copal ECC)

## Model description

Probabilistic PV forecasts for the Copal Supermarket energy community (973.81 kWc, Luxembourg, Leneda 15-minute
metering): P10 / P50 / P90 in kW for every 15-minute slot of the next 24 hours, from LightGBM quantile
regressors of the **clear-sky index**, **numerical-weather-prediction inputs** (Open-Meteo Previous Runs) and a
**conformally recalibrated** band.

| Block | Lead time | Issued | Files |
|---|---|---|---|
| intraday | 0–6 h | every 2 h, 04–18 UTC | `pv_intraday_q10/q50/q90.txt` |
| day-ahead | 6–24 h | every 6 h, 00/06/12/18 UTC | `pv_day_ahead_q10/q50/q90.txt` |

| Field | Value |
|---|---|
| Algorithm | LightGBM quantile regression, 3 models per block (`{"n_estimators": 300, "max_depth": 4, "num_leaves": 16, "learning_rate": 0.05, "min_child_samples": 40, "subsample": 0.85}`) |
| Target | clear-sky index (PV ÷ clear-sky power), clipped to [0, 1.3] |
| Envelope | slope: 0.799626 kW per W/m² of clear-sky GHI, cap 662.723 kW |
| Features | 24 — solar geometry, lead time, recent and 24 h-lagged observations, ICON-EU weather forecasts (GHI, DNI, DHI, cloud, temperature, wind), forecast clear-sky index and a 3-model ensemble mean |
| Weather | Open-Meteo Previous Runs: forecasts issued 24 h (lead ≤ 18 h) or 48 h before the valid time; a run is usable 6 h after its nominal time |
| Band | raw quantiles, plus conformal offsets per lead bucket (frozen from the last 45 days of the calibration window; online update recommended) |
| Trained on | Copal data before 19 Nov 2025; band calibrated on 19 Nov 2025 → 18 Jan 2026 |

## Repository contents

| File | Content |
|---|---|
| `pv_<block>_<q>.txt` | LightGBM text models — no pickle, loadable by any LightGBM ≥ 4 |
| `model_config.json` | feature order, lead buckets, envelope, weather specification, band offsets, windows |
| `example.py` | short script: loads the sample data and runs the models (see *Installation and inference*) |
| `example_features.csv` | small sample data set of ready-made feature rows (see *Inputs and data*) |
| `requirements.txt` | the environment in which the models were exported and the example runs |
| `metrics.json` | validation, ablation, bootstrap, conformal, external check, decisions |
| `LICENSE` | MIT licence |

## Inputs and data

### Training data

Leneda 15-minute smart-meter production of the Copal Supermarket energy community PV plant (OBIS 1-1:2.29.0),
11 Oct 2023 → 18 Jan 2026, as published with the EnerTEF TEF-EV service repositories
(`Data/ECC_master_PV_EMOB1_EMOB2_15min.csv` in the GitHub repository), plus Open-Meteo Previous Runs forecasts (CC BY 4.0) for the
weather features.

### Sample data: `example_features.csv`

Real Copal data that was **not used for fitting**: 5 consecutive days from 24 Nov 2025, a few days after the training window ends and before the 45 days that the band offsets were calibrated on. It holds the **intraday** block issued at 08:00 UTC (120 daylight slots) and the **day-ahead** block issued at 18:00 UTC (155 slots) of each day, with the Open-Meteo previous-run weather forecasts that were available at each issue time (CC BY 4.0, non-commercial).

| Column | Meaning |
|---|---|
| `block`, `issue`, `ts` | horizon block, issue time and target slot (UTC) |
| 24 feature columns | exactly the model inputs, named as in `model_config.json` (`-1` = missing) |
| `actual_kw` | measured plant output of the slot |
| `pers_kw` | the 24 h persistence forecast for the slot (the reference the skill is computed against) |

## Installation and inference

### Requirements

```
lightgbm==4.7.0
numpy==2.4.6
pandas==3.0.6
```

### Run the bundled example

```bash
pip install -r requirements.txt
python example.py
```

It prints the first rows of the forecast and, per block, the error against the measured output and against persistence. The last lines are:

```
intraday  n= 120 | P50 MAE  20.29 kW (nMAE 2.08 % of kWc) | persistence MAE  34.50 kW | skill  41.2 % | P10-P90 coverage  88 %
day_ahead n= 155 | P50 MAE  18.45 kW (nMAE 1.89 % of kWc) | persistence MAE  28.26 kW | skill  34.7 % | P10-P90 coverage  86 %
```

### Predict from your own features

`example.py` contains the complete `predict(block, X)` function: LightGBM quantiles of the clear-sky index, the frozen conformal band offsets
per lead bucket, and the scaling by clear-sky power, capped at the plant envelope. `X` needs the feature columns of
`model_config.json` (`blocks.<block>.features`); the feature builder (clear-sky power from solar position, history lookups strictly before the
issue time, previous-run weather per `model_config.json["weather"]`) is part of the notebook `ECC_PV_Forecasting.ipynb` §3–§4 in the GitHub
repository — use it unchanged so the inputs match training.

## Evaluation

### Validation — five expanding-window folds, 1 Jan 2025 → 18 Jan 2026 (every season)

Daytime 15-minute slots, pooled. `base` = history-only features and slope envelope; the shipped configuration is
`+weather`. nMAE is a percentage of the nameplate; skill is relative to 24 h persistence.

| block | configuration | slots | nMAE (% of kWc) | skill vs persistence (%) | bias (kW) | P10–P90 coverage (%) | interval score (kW) |
|---|---|---|---|---|---|---|---|
| intraday | base | 47375 | 5.90 | 19.01 | -14.47 | 63.54 | 256.50 |
| intraday | +weather | 47375 | 4.59 | 37.01 | -8.87 | 65.80 | 204.39 |
| intraday | +envelope | 47375 | 6.00 | 17.60 | -15.38 | 64.29 | 260.04 |
| intraday | +weather +envelope | 47375 | 4.52 | 37.91 | -7.32 | 65.31 | 205.95 |
| day_ahead | base | 51423 | 7.04 | -1.13 | -18.80 | 60.22 | 292.64 |
| day_ahead | +weather | 51423 | 4.56 | 34.55 | -9.21 | 64.54 | 206.77 |
| day_ahead | +envelope | 51423 | 6.77 | 2.79 | -14.33 | 59.58 | 294.57 |
| day_ahead | +weather +envelope | 51423 | 4.50 | 35.42 | -6.66 | 66.07 | 200.82 |

Pooled P10–P90 coverage of the shipped configuration (nominal 80 %): intraday 65.8 % raw → 78.0 % recalibrated; day-ahead 64.5 % → 77.9 %.

### Against the previous release on its own hold-out (19 Nov 2025 → 18 Jan 2026, winter)

| block | model | slots | nMAE (%) | skill vs persistence (%) | coverage raw (%) | bias (kW) |
|---|---|---|---|---|---|---|
| intraday | previous release (history-only, scikit-learn) | 5265 | 1.87 | 26.06 | 71.70 | -0.24 |
| intraday | current release (+weather) | 5265 | 1.69 | 33.75 | 69.74 | 2.46 |
| day_ahead | previous release (history-only, scikit-learn) | 5253 | 2.38 | 4.78 | 67.30 | -2.64 |
| day_ahead | current release (+weather) | 5253 | 1.74 | 31.10 | 70.32 | 1.07 |

### External check — Elia Luxembourg-province PV (a different source, not Copal)

Copal-trained models, envelope refitted on the Elia series, 19 Nov 2025 → 30 Sep 2026 (includes spring and summer 2026),
next-day forecasts issued 18 UTC, same slots:

| forecast | slots | nMAE (% of capacity) | bias (kW) | R² |
|---|---|---|---|---|
| base | 14262 | 7.35 | 4.33 | 0.65 |
| +weather | 14262 | 5.23 | 20.42 | 0.82 |
| +envelope | 14262 | 7.04 | 3.04 | 0.69 |
| +weather +envelope | 14262 | 4.50 | 11.33 | 0.87 |
| Elia day-ahead 6 PM | 14262 | 3.63 | 17.14 | 0.92 |
| persistence (24 h) | 14262 | 7.01 | -0.57 | 0.63 |

## Reproduce the workflow

The models, their validation and this card are produced by `ECC_PV_Forecasting.ipynb` in the project repository
([TEF-EV-Service-2----Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities-](https://github.com/ENERTEF/TEF-EV-Service-2----Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities-)); it needs the Copal CSV in `Data/` and the cached Open-Meteo / Elia series in
`Data/external/` (downloaded on first run). The notebook's export cell re-loads the files in this package with nothing but LightGBM and
reproduces the in-memory forecasts, and its example cell runs `example.py` and checks its numbers against the in-memory ones.

## Intended uses and limitations

**Intended use:** day-ahead and intraday PV generation forecasting for the Copal plant, and as a template for similar plants after
refitting the envelope and the models. **Not intended for:** other sites without refitting, or safety-critical grid control.

- Single plant; the envelope and the learned relation are Copal's. On another source the clear-sky shape differs and the bias grows (see the external check); retrain or at least refit the envelope per site.
- Weather forecasts come from Open-Meteo's free API (CC BY 4.0, non-commercial use only); a production service needs a subscription or another feed with the same previous-run semantics. The archive starts on 19 Jan 2024.
- Anomalous winter output (e.g. January 2026, when the measured output fell below the model's P10 in a large share of slots; the cause was not investigated) cannot be anticipated from these inputs.
- The shipped band offsets are frozen; coverage is closest to nominal when they are updated online from recent outcomes.
- The shipped models were trained on data older than 60 days before the last Copal observation; refit when a newer Leneda export is available.

## License and project references

Model and code: MIT (`LICENSE`). Part of the EnerTEF project ([huggingface.co/EnerTEF](https://huggingface.co/EnerTEF)), TEF-EV experimentation
facility (Leneda, Luxembourg), Service 2 (localised PV generation forecasting, D2.2 §2.5.2). Code and the full experiment:
[TEF-EV-Service-2----Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities-](https://github.com/ENERTEF/TEF-EV-Service-2----Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities-). Data and attribution: Copal energy-community PV production (Leneda, as published with the
EnerTEF service repositories); weather: Open-Meteo.com (CC BY 4.0, non-commercial); external check: Elia Open Data.
