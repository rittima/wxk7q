"""Build the local data cache used by the API.

    python -m scripts.build_cache              # fetch real data from Elexon
    python -m scripts.build_cache --synthetic  # generate clearly-labelled DEMO data (no network)
"""
import argparse
import json
from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from app import config, elexon

DEL_START, DEL_END = date(2026, 1, 2), date(2026, 2, 1)
PUB_START, PUB_END = date(2025, 12, 30), date(2026, 1, 31)


def synthetic():
    rng = np.random.default_rng(42)
    idx = pd.date_range("2025-12-30", "2026-02-02", freq="30min", tz="UTC", inclusive="left")
    x = np.zeros(len(idx))
    for i in range(1, len(x)):
        x[i] = 0.997 * x[i - 1] + rng.normal(0, 0.07)
    actual = np.clip(9000 + 4800 * (x - x.mean()) / x.std(), 300, 22000)
    act = pd.DataFrame({"startTime": idx, "actual": actual.round(1)})
    persistent = np.convolve(rng.normal(0, 1, len(idx)), np.ones(8) / 8, mode="same")  # smooth model error shared across runs
    persistent /= persistent.std()
    pos = {t: i for i, t in enumerate(idx)}
    rows = []
    for pub in pd.date_range("2025-12-30", "2026-01-31 23:00", freq="1h", tz="UTC"):
        targets = idx[(idx >= pub + pd.Timedelta(hours=1)) & (idx <= pub + pd.Timedelta(hours=config.MAX_HORIZON_H))]
        h = (targets - pub).total_seconds().to_numpy() / 3600
        i = np.array([pos[t] for t in targets])
        sd = 120 + 28 * h
        f = actual[i] + sd * (0.9 * persistent[i] + 0.25 * rng.normal(0, 1, len(i))) - 60
        rows.append(pd.DataFrame({"startTime": targets, "publishTime": pub, "generation": np.clip(f, 0, None).round(1)}))
    fc = pd.concat(rows, ignore_index=True)
    fc = fc[(fc.startTime >= "2026-01-01") & (fc.startTime < "2026-02-02")]
    act = act[(act.startTime >= "2026-01-01") & (act.startTime < "2026-02-02")]
    return fc, act


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true", help="generate demo data instead of calling Elexon")
    args = ap.parse_args()
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.synthetic:
        fc, act = synthetic()
        source = "synthetic"
    else:
        t_from = datetime(2026, 1, 1, tzinfo=timezone.utc)
        t_to = datetime(2026, 2, 2, tzinfo=timezone.utc)
        act = elexon.fetch_actuals(date(2026, 1, 1), DEL_END)
        fc = elexon.fetch_forecasts(PUB_START, PUB_END, t_from, t_to)
        source = "elexon"

    fc.to_csv(config.DATA_DIR / "wind_forecasts.csv.gz", index=False, compression="gzip")
    act.to_csv(config.DATA_DIR / "wind_actuals.csv", index=False)
    (config.DATA_DIR / "meta.json").write_text(json.dumps({
        "source": source,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "forecast_rows": int(len(fc)),
        "actual_rows": int(len(act)),
    }, indent=2))
    print(f"[{source}] wrote {len(fc):,} forecast rows and {len(act):,} actual rows to {config.DATA_DIR}")


if __name__ == "__main__":
    main()
