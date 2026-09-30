---
library_name: scikit-learn
license: mit
pipeline_tag: tabular-regression
tags:
- energy
- solar
- pv-forecasting
- probabilistic-forecasting
- quantile-regression
- gradient-boosting
- energy-community
- enertef
---

# Service 2 — localised PV generation forecasting (Copal ECC)

Probabilistic **PV generation** models for the EnerTEF TEF-EV localised PV forecasting service
(D2.2 §2.5.2), trained on the Copal Supermarket energy community in Luxembourg (973.81 kWc,
Leneda 15-minute metering). They predict the **clear-sky index** (PV ÷ clear-sky power) at the
q10 / q50 / q90 quantiles; multiplied by the clear-sky power of the fitted plant envelope, they give
P10 / P50 / P90 generation in kW for every 15-minute slot of the next **24 hours**.

Code, data and the full experiment: [TEF-EV-Service-2----Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities-](https://github.com/ENERTEF/TEF-EV-Service-2----Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities-) (notebook `ECC_PV_Forecasting.ipynb`).

| Block | Lead time | Issued | Model file |
|---|---|---|---|
| intraday | 0–6 h | every 2 h, 04–18 UTC | `pv_quantile_intraday.joblib` |
| day-ahead | 6–24 h | every 6 h, 00/06/12/18 UTC | `pv_quantile_day_ahead.joblib` |

## Model

| Field | Value |
|---|---|
| Algorithm | scikit-learn GBR — 3 quantile regressors (q10 / q50 / q90) per block, chosen by the bake-off below |
| Parameters | `{"loss": "quantile", "init": "zero", "n_estimators": 300, "max_depth": 4, "learning_rate": 0.05, "min_samples_leaf": 40, "subsample": 0.85, "random_state": 42}` |
| Target | clear-sky index, clipped to [0, 1.3] |
| Features | 22 (solar geometry, lead time, recent and 24 h-lagged observations; NWP columns reserved, `-1` in this offline release) |
| Weather inputs | none (offline) |
| Training window | 11 Oct 2023 → 19 Nov 2025 |
| Hold-out | 19 Nov 2025 → 18 Jan 2026 (60 days, winter) |
| Version | 1.0.0 (2026-09-30) |

## Hold-out accuracy (daytime 15-minute slots, out-of-sample)

| | MAE (kW) | RMSE (kW) | R² | P10–P90 coverage (%) | persistence MAE (kW) | skill vs persistence (%) |
|---|---|---|---|---|---|---|
| intraday | 18.19 | 24.73 | 0.51 | 71.70 | 24.61 | 26.06 |
| day_ahead | 23.23 | 29.98 | 0.29 | 67.30 | 24.39 | 4.78 |

By forecast horizon:

| | MAE (kW) | nMAE (% of kWc) | R² | P10–P90 coverage (%) | skill vs persistence (%) |
|---|---|---|---|---|---|
| < 1 h | 12.09 | 1.24 | 0.75 | 75.20 | 49.03 |
| 1–6 h | 19.56 | 2.01 | 0.46 | 70.90 | 21.17 |
| day-ahead (6–24 h) | 23.23 | 2.38 | 0.29 | 67.30 | 4.78 |

Without weather inputs the day-ahead model learns the climatology of the clear-sky index, so it sits
close to persistence; the intraday model earns its skill from recent observations. NWP features
(e.g. Open-Meteo, MeteoLux) are what lifts day-ahead skill.

## Model selection — why scikit-learn GBR

scikit-learn GBR (the incumbent), LightGBM and XGBoost were trained on identical samples and hold-out,
with the same capacity translated to each library and no per-library tuning, over three seeds. The rule
was fixed before the run: a challenger replaces GBR only if its P50 MAE is at least 3 % lower
averaged over the blocks, the gap exceeds the seed-to-seed range, it is not worse on any block, and its
P10–P90 coverage drops by at most 5 points on every block.

| Algorithm | intraday P50 MAE (kW) | day_ahead P50 MAE (kW) | P10–P90 coverage (intraday / day_ahead) | Fit time (all blocks, per seed) | Verdict |
|---|---|---|---|---|---|
| scikit-learn GBR | 18.2 [18.2–18.3] | 23.3 [23.2–23.4] | 72.4 / 66.4 % | 496 s | incumbent — **selected** |
| LightGBM | 17.7 [17.7–17.9] | 22.7 [22.4–23.0] | 71.1 / 69.4 % | 5 s | rejected — mean MAE gain +2.5 % is below the 3 % bar |
| XGBoost | 17.9 [17.9–17.9] | 22.8 [22.4–23.2] | 71.5 / 69.5 % | 36 s | rejected — mean MAE gain +2.0 % is below the 3 % bar |

MAE is the mean [min–max] over seeds 42, 43, 44.

**scikit-learn GBR is retained** — no challenger cleared the rule.

Per-seed results: `benchmark.json`.

## Files

| File | Content |
|---|---|
| `pv_quantile_<block>.joblib` | dict with `features` (order), `quantiles` (`q10`/`q50`/`q90` estimators) and metadata |
| `envelope.json` | fitted plant envelope: `kw_per_wm2` (clear-sky power slope) and `max_kw` (cap) |
| `metrics.json` | hold-out metrics per block and horizon, windows, parameters, library versions |
| `benchmark.json` | algorithm bake-off: per-seed results, rule, verdicts |

## Usage

```python
import json
import joblib
import numpy as np

bundle = joblib.load("pv_quantile_intraday.joblib")
envelope = json.load(open("envelope.json"))
# X: rows of the 22 features in bundle["features"] order — built exactly as in the notebook (§4)
kcs = np.sort([np.maximum(est.predict(X), 0) for est in bundle["quantiles"].values()], axis=0)
clear_sky_kw = np.minimum(envelope["kw_per_wm2"] * clear_sky_ghi_wm2, envelope["max_kw"])
p10_kw, p50_kw, p90_kw = np.minimum(kcs * clear_sky_kw, envelope["max_kw"])
```

The feature builder (solar geometry, clear-sky model, leakage-safe history lookups) is part of the
notebook in the GitHub repository; use it unchanged so the inputs match training.

## Data

Leneda 15-minute smart-meter production of the Copal Supermarket energy community PV plant
(OBIS 1-1:2.29.0), 11 Oct 2023 → 18 Jan 2026, as published with the EnerTEF TEF-EV service
repositories (`Data/ECC_master_PV_EMOB1_EMOB2_15min.csv`).

## Limitations

- Single plant, empirical envelope (tilt and azimuth unknown): a site-specific model, not a general PV model.
- Offline release without weather inputs — day-ahead skill over persistence is small.
- P10 / P90 are raw quantile outputs (no conformal recalibration); coverage is reported above.
- Horizon ends at 24 h by design (intraday + day-ahead).

## Attribution

EnerTEF — TEF-EV experimentation facility (Leneda, Luxembourg), Service 2. MIT licence.
