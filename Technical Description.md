TEF_EV-ECC_PV_FORECASTING
=========================

**Localised PV generation forecasting for the Copal Supermarket energy community (ECC)**

Overview
--------

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
builds the features, validates and selects the configuration, trains and evaluates the models, and
exports them with their Hugging Face model card. It depends only on `requirements.txt`.

Method
------

*   **Target — clear-sky index.** The models learn PV ÷ clear-sky power rather than power, which
    removes the seasonal and diurnal solar geometry from what has to be learned.

*   **Physics.** NOAA solar position and the Ineichen–Perez clear-sky model (Linke turbidity 3.0),
    evaluated at the midpoint of each 15-minute slot, plus the solar azimuth, which the learned
    envelope needs. Plant tilt and azimuth are unknown, so the clear-sky power is an **empirical
    envelope**: 0.799626 kW per W/m² of clear-sky GHI (99.5th percentile of PV / clear-sky GHI over
    the well-lit slots), capped at 662.723 kW (99.9th percentile of output) — versus the 973.81 kWc
    nameplate. A **learned envelope** (a smooth conditional upper quantile of output on sun
    elevation, azimuth and season) was also implemented and tested but did not clear its adoption
    rule, so the slope envelope ships.

*   **Features (24 per issue time and target slot).** Clear-sky power and GHI, cos(zenith),
    time-of-day and day-of-year harmonics, lead time, the recent clear-sky index (last 3 h for
    intraday, previous day for day-ahead), the last observation (intraday), the same slot 24 h
    earlier, and ICON-EU weather forecasts (GHI, DNI, DHI, cloud cover, temperature, wind) with the
    forecast clear-sky index and a 3-model ensemble mean. The history-only configuration (`base`)
    uses 14 of them; the rest are weather.

    Weather values come from the Open-Meteo *Previous Runs* archive: a value is what a model
    predicted 24 h or 48 h before the valid time (the API's fixed previous-run offsets), and a run
    counts as available only 6 h after its nominal time, so nothing from the future leaks into a
    forecast.

*   **Leakage rules.** Every history lookup uses only observations strictly before the issue time;
    training rows whose target lies beyond the training cut-off are purged; the envelope is refitted
    inside each fold on training data only; conformal scores use only outcomes already observed at
    the issue time.

*   **Models.** One model per horizon block, each made of three LightGBM quantile regressors
    (q10 / q50 / q90; 300 trees, depth 4, 16 leaves, learning rate 0.05, minimum leaf 40, row
    subsampling 0.85) of the clear-sky index. Quantiles are clipped at zero, sorted, multiplied by
    the clear-sky power and capped at the envelope.

*   **Band.** Raw quantile outputs are widened (or narrowed) per lead bucket by **conformalized
    quantile regression** offsets computed from the model's own recent out-of-sample errors. The
    shipped package carries frozen offsets; an online update is recommended where a feed of recent
    outcomes is available.

Validation
----------

Configuration choices are decided on a **rolling-origin validation** — five expanding-window test
folds covering 1 Jan 2025 → 18 Jan 2026, i.e. every season — on a factorial ablation
(`base`, `+weather`, `+envelope`, `+weather +envelope`), with the adoption rules fixed before the
results were looked at. Pooled P50 accuracy of the shipped configuration (`+weather`, slope
envelope, conformal band):

| Block | nMAE (% of kWc) | Skill vs persistence (%) | P10–P90 coverage, raw → conformal (%) |
|---|---|---|---|
| intraday | 4.59 | +37.0 | 65.8 → 78.0 |
| day-ahead | 4.56 | +34.6 | 64.5 → 77.9 |

Weather inputs are the decisive lever: they cut the day-ahead P50 MAE by 35.3 % (90 % bootstrap
interval −38.6 … −31.8 %) and raise day-ahead skill over persistence from −1.1 % to +34.6 %, in
every fold. On the previous release's 60-day winter hold-out, like for like, day-ahead nMAE falls
from 2.38 % to 1.74 % and skill rises from +4.8 % to +31.1 %; intraday from 1.87 % to 1.69 % and
from +26.1 % to +33.8 %.

**External check.** Trained on Copal only and scored on the Elia Luxembourg-province series
(weather and envelope refitted, same inputs) over 19 Nov 2025 → 30 Sep 2026: nMAE 5.23 % of
capacity, against 7.01 % for 24 h persistence and 3.63 % for Elia's own weather-driven day-ahead
forecast. The models remain Copal models: on the other source the site-shape mismatch shows up as a
bias.

Data Sources
------------

*   **Smart-meter measurements** (Leneda, 15-minute resolution)

    *   PV production `PV_TotalProduction_kW` (OBIS 1-1:2.29.0), 11 Oct 2023 → 18 Jan 2026,
        in `Data/ECC_master_PV_EMOB1_EMOB2_15min.csv`

*   **Meteorological data** — Open-Meteo *Previous Runs* API (CC BY 4.0; the free tier is for
    non-commercial use only), hourly, for the plant location: ICON-EU (GHI, DNI, DHI, cloud cover,
    temperature, wind) plus ECMWF IFS and ARPEGE GHI. The archive starts in January 2024.

*   **External evaluation** — Elia Open Data (ODS032), Luxembourg-province PV, for the transfer
    check only.

Outputs
-------

*   Trained models `Data/models/pv_intraday_q10/q50/q90.txt` and
    `Data/models/pv_day_ahead_q10/q50/q90.txt` (LightGBM text — no pickle), for Hugging Face as
    [`EnerTEF/EV-Service2-Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities`](https://huggingface.co/EnerTEF/EV-Service2-Localized-PV-Generation-Forecasting-Service-for-Smart-Energy-Communities)
    (upload is opt-in, notebook §13)

*   `model_config.json` (feature order, envelope, weather specification, frozen band offsets),
    validation metrics (`metrics.json`), the pinned `requirements.txt`, the `LICENSE` and the model
    card (`README.md`) in `Data/models/`. Following the EnerTEF upload guidelines the package also
    carries a short script, `example.py`, that loads a small sample data set,
    `example_features.csv` (real Copal data from the hold-out, ready-made feature rows), and runs the
    models on it; the notebook runs that script from an isolated copy of the package and checks its
    numbers against the in-memory models.

*   24-hour P10 / P50 / P90 forecast packages and the fold evaluation by block, by horizon and by
    lead time (notebook §7–§12)

How to run
----------

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate            # macOS / Linux: python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
jupyter lab ECC_PV_Forecasting.ipynb
```

Run all cells from the repository root. The notebook downloads the weather (and Elia) series on
first run into `Data/external/`. Publishing to Hugging Face (§13) is opt-in and needs a token that
may write to the EnerTEF organisation (`hf auth login`; a fine-grained token must list EnerTEF under
*Org permissions*); the cell checks the token, creates a missing repo as private and explains any
missing permission.

Limitations and next steps
--------------------------

*   Single plant; the envelope and the learned relation are Copal's. On another source the clear-sky
    shape differs and the bias grows (see the external check): retrain or at least refit the envelope
    per site.

*   The weather archive starts in January 2024, so the first fold trains on about ten months of
    weather.

*   The shipped band offsets are frozen; coverage is closest to nominal when they are updated online
    from recent outcomes.

*   The Leneda export ends on 18 Jan 2026; Copal's spring and summer 2026 are covered only through
    the Elia proxy. Refit when a newer export is available.

*   Production use of Open-Meteo's free API is outside its terms (non-commercial only).
