TEF_EV-ECC_PV_FORECASTING
=========================

**Localised PV generation forecasting for the Copal Supermarket energy community (ECC)**

Overview (version 1.0)
----------------------

**TEF_EV-ECC_PV_FORECASTING** forecasts the PV production of the Copal Supermarket energy
community (973.81 kWc, 6.48714 E / 49.70673 N, Leneda 15-minute metering) for the next
**24 hours**:

*   **Intraday** — 0–6 h ahead, issued every 2 hours through the daylight window (04–18 UTC)

*   **Day-ahead** — 6–24 h ahead, issued every 6 hours (00, 06, 12, 18 UTC), so an evening
    issue forecasts the whole next-day daylight profile

Every forecast is **probabilistic** — P10 / P50 / P90 in kW for each 15-minute slot — and
**physically bounded** by a plant envelope fitted from history. Accuracy is always reported
against **persistence** (the same slot 24 h earlier), the reference the service specification
requires.

The complete implementation is the notebook **`ECC_PV_Forecasting.ipynb`**: it loads the data,
builds the features, selects the learning algorithm, trains and evaluates the models, and exports
them with their Hugging Face model card. It depends only on `requirements.txt`.

Method
------

*   **Target — clear-sky index.** The models learn PV ÷ clear-sky power rather than power, which
    removes the seasonal and diurnal solar geometry from what has to be learned.

*   **Physics.** NOAA solar position and the Ineichen–Perez clear-sky model (Linke turbidity 3.0),
    evaluated at the midpoint of each 15-minute slot. Plant tilt and azimuth are unknown, so the
    clear-sky power is an **empirical envelope**: 0.798 kW per W/m² of clear-sky GHI (99.5th
    percentile of PV / clear-sky GHI over 26,111 well-lit slots), capped at 662 kW (99.9th
    percentile of output) — versus the 973.81 kWc nameplate.

*   **Features (22 per issue time and target slot).** Clear-sky power and GHI, cos(zenith),
    time-of-day and day-of-year harmonics, lead time, the recent clear-sky index (last 3 h for
    intraday, previous day for day-ahead), the last observation (intraday), and the same slot 24 h
    earlier. Seven NWP weather columns are reserved and set to `-1` in this offline release.

*   **Leakage rule.** Every history lookup uses only observations strictly before the issue time,
    so training contains nothing a live forecast could not have known.

*   **Models.** One model per horizon block, each made of three quantile regressors
    (q10 / q50 / q90). Quantiles are clipped at zero, sorted, multiplied by the clear-sky power
    and capped at the envelope.

Algorithm selection
-------------------

scikit-learn `GradientBoostingRegressor` (the incumbent), **LightGBM** and **XGBoost** were
compared on identical samples and hold-out, with the same capacity translated to each library
(300 trees, depth 4, learning rate 0.05, minimum leaf 40, row subsampling 0.85), no per-library
tuning, and three seeds. The rule was **fixed before the experiment**: a challenger replaces GBR
only if its P50 MAE is at least 3 % lower averaged over both blocks, the gap exceeds the
seed-to-seed range, it is not worse on either block, and its P10–P90 coverage drops by at most
5 points.

| Algorithm | Intraday MAE (kW) | Day-ahead MAE (kW) | Verdict |
|---|---|---|---|
| scikit-learn GBR | 18.2 | 23.3 | **retained** |
| LightGBM | 17.7 | 22.7 | rejected — mean gain +2.5 %, below the 3 % bar |
| XGBoost | 17.9 | 22.8 | rejected — mean gain +2.0 %, below the 3 % bar |

The challengers are 2–2.5 % better on average — consistently, beyond the seed-to-seed spread,
but below the materiality bar fixed before the run, so the incumbent stays. The limiting factor
is the missing weather input, not the learner. Per-seed results: `Data/models/benchmark.json`.

Data Sources
------------

*   **Smart-meter measurements** (Leneda, 15-minute resolution)

    *   PV production `PV_TotalProduction_kW` (OBIS 1-1:2.29.0), 11 Oct 2023 → 18 Jan 2026,
        in `Data/ECC_master_PV_EMOB1_EMOB2_15min.csv`

*   **Meteorological data** — none in version 1.0. The feature vector reserves the NWP columns
    (GHI / DNI / DHI, cloud cover, temperature, wind) for Open-Meteo or MeteoLux forecasts.

Results (version 1.0)
---------------------

Hold-out: the last 60 days (19 Nov 2025 → 18 Jan 2026, winter), daytime 15-minute slots,
out-of-sample. nMAE is relative to the 973.81 kWc nameplate; the nominal P10–P90 coverage is 80 %.

| Horizon | MAE | nMAE | R² | P10–P90 coverage | Skill vs persistence |
|---|---|---|---|---|---|
| < 1 h | 12.1 kW | 1.2 % | 0.75 | 75.2 % | +49.0 % |
| 1–6 h | 19.6 kW | 2.0 % | 0.46 | 70.9 % | +21.2 % |
| Day-ahead (6–24 h) | 23.2 kW | 2.4 % | 0.29 | 67.3 % | +4.8 % |

Skill decays from about 49 % at the shortest lead to a few percent after 6 h: intraday forecasts
earn their skill from recent observations. Without weather inputs, the day-ahead model can only
learn the climatology of the clear-sky index, so it stays close to persistence (+4.8 %) — adding
NWP forecasts is the lever for day-ahead accuracy.

Outputs (version 1.0)
---------------------

*   Trained models `Data/models/pv_quantile_intraday.joblib` and
    `Data/models/pv_quantile_day_ahead.joblib` (q10 / q50 / q90 per block), published on
    Hugging Face as [`EnerTEF/Service2-PvForecast`](https://huggingface.co/EnerTEF/Service2-PvForecast)

*   Fitted plant envelope (`envelope.json`), hold-out metrics (`metrics.json`), the algorithm
    bake-off (`benchmark.json`) and the model card (`README.md`) in `Data/models/`

*   24-hour P10 / P50 / P90 forecast packages and the hold-out evaluation by block, by horizon and
    by lead time (notebook §6–§7)

How to run
----------

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
jupyter lab ECC_PV_Forecasting.ipynb
```

Run all cells from the repository root (about 30 minutes, almost all of it the bake-off). Publishing to
Hugging Face (§9) is opt-in and needs a write token (`hf auth login`).

Limitations and next steps
--------------------------

*   No weather inputs yet: day-ahead skill over persistence is small. Next step: Open-Meteo
    historical-forecast / MeteoLux NWP features.

*   Empirical envelope: tilt and azimuth of the plant are unknown; a transposition model needs them.

*   P10–P90 covers 67–75 % against a nominal 80 %; conformal recalibration would tighten this.

*   Single plant; the horizon ends at 24 h by design.
