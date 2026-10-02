"""Run the Service 2 PV forecasting models (LightGBM text files) on the bundled sample.

    pip install -r requirements.txt
    python example.py

example_features.csv holds ready-made feature rows: real Copal energy-community data, a few days after the training window, with the
Open-Meteo previous-run weather forecasts that were available at each issue time. The script predicts P10 / P50 / P90 in kW and
compares them with the measured output and with 24 h persistence. Building the features for other times is the notebook's job
(solar geometry, clear-sky power, history lookups strictly before the issue time, weather per model_config.json).
"""
import json
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

here = Path(__file__).resolve().parent
cfg = json.loads((here / "model_config.json").read_text(encoding="utf-8"))
data = pd.read_csv(here / "example_features.csv", parse_dates=["issue", "ts"])
KCS_MAX, CAP_KW = 1.3, cfg["envelope"]["max_kw"]


def predict(block, X):
    # features -> P10 / P50 / P90 in kW (clear-sky index quantiles, frozen conformal band offsets per lead bucket, scaled by clear-sky power)
    spec = cfg["blocks"][block]
    boosters = {q: lgb.Booster(model_file=str(here / f)) for q, f in spec["quantile_files"].items()}
    q = np.sort(np.clip([boosters[k].predict(X[spec["features"]]) for k in ("q10", "q50", "q90")], 0.0, KCS_MAX), axis=0)
    lo, hi = q[0].copy(), q[2].copy()
    if cfg["conformal"]["enabled"]:
        lead = X["lead_time_hours"].to_numpy()
        for o in spec["band_offsets"]:
            m = (lead >= o["lead_from_h"]) & (lead < o["lead_to_h"])
            lo[m], hi[m] = lo[m] - o["lower"], hi[m] + o["upper"]
        lo, hi = np.clip(np.minimum(lo, q[1]), 0.0, KCS_MAX), np.clip(np.maximum(hi, q[1]), 0.0, KCS_MAX)
    cs = X["clear_sky_kw"].to_numpy()
    return np.minimum(lo * cs, CAP_KW), np.minimum(q[1] * cs, CAP_KW), np.minimum(hi * cs, CAP_KW)


for block, d in data.groupby("block", sort=False):
    p10, p50, p90 = predict(block, d)
    a, pers = d.actual_kw.to_numpy(), d.pers_kw.to_numpy()
    mae, mae_pers = np.mean(np.abs(p50 - a)), np.mean(np.abs(pers - a))
    print(d.assign(p10=p10, p50=p50, p90=p90)[["ts", "actual_kw", "p10", "p50", "p90"]].head(4).round(1).to_string(index=False))
    print(f"{block:9s} n={len(d):4d} | P50 MAE {mae:6.2f} kW (nMAE {100 * mae / cfg['capacity_kwc']:.2f} % of kWc) | persistence MAE {mae_pers:6.2f} kW"
          f" | skill {100 * (1 - mae / mae_pers):5.1f} % | P10-P90 coverage {100 * np.mean((p10 <= a) & (a <= p90)):3.0f} %\n")
