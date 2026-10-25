"""Pure analysis functions (no I/O) so they are easy to test.

Sign convention: error = forecast - actual. Positive => the forecast over-estimated wind,
so a buyer relying on it would under-buy other generation.
"""
from datetime import date, timedelta

import numpy as np
import pandas as pd

from .config import TZ


def parse_cutoff(cutoff_hhmm: str) -> tuple[int, int]:
    h, m = cutoff_hhmm.split(":")
    h, m = int(h), int(m)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError("cutoff must be HH:MM")
    return h, m


def cutoff_utc(start_times: pd.Series, cutoff_hhmm: str) -> pd.Series:
    """For each target time, the UTC instant of the cutoff on the *previous* London day."""
    h, m = parse_cutoff(cutoff_hhmm)
    local_day = start_times.dt.tz_convert(TZ).dt.tz_localize(None).dt.normalize()
    cutoff_local = local_day - pd.Timedelta(days=1) + pd.Timedelta(hours=h, minutes=m)
    return cutoff_local.dt.tz_localize(TZ, ambiguous="NaT", nonexistent="shift_forward").dt.tz_convert("UTC")


def decision_forecasts(fc: pd.DataFrame, cutoff_hhmm: str) -> pd.DataFrame:
    """The latest forecast for each target half hour that was published at or before the cutoff.

    Forecasts published after the cutoff are ignored: the buyer could not have seen them.
    """
    df = fc.copy()
    df["cutoff"] = cutoff_utc(df["startTime"], cutoff_hhmm)
    df = df[df["publishTime"] <= df["cutoff"]]
    df = df.sort_values("publishTime").groupby("startTime", as_index=False).last()
    local = df["startTime"].dt.tz_convert(TZ)
    df["delivery_date"] = local.dt.strftime("%Y-%m-%d")
    df["hour"] = local.dt.hour
    df["label"] = local.dt.strftime("%H:%M")
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    return df.rename(columns={"generation": "forecast"}).reset_index(drop=True)


def join_actuals(decisions: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    df = decisions.merge(actuals, on="startTime", how="left")
    df["error"] = df["forecast"] - df["actual"]
    return df


def _r(x, nd=1):
    return None if x is None or pd.isna(x) else round(float(x), nd)


def metrics(frame: pd.DataFrame) -> dict:
    v = frame.dropna(subset=["actual"])
    if v.empty:
        return {"n": 0, "mae": None, "rmse": None, "bias": None, "mape_pct": None,
                "p50_abs": None, "p90_abs": None, "p95_abs": None}
    e = v["error"]
    ae = e.abs()
    nonzero = v["actual"] > 0
    mape = (ae[nonzero] / v.loc[nonzero, "actual"]).mean() * 100 if nonzero.any() else None
    return {
        "n": int(len(v)),
        "mae": _r(ae.mean()),
        "rmse": _r(np.sqrt((e**2).mean())),
        "bias": _r(e.mean()),
        "mape_pct": _r(mape),
        "p50_abs": _r(ae.quantile(0.5)),
        "p90_abs": _r(ae.quantile(0.9)),
        "p95_abs": _r(ae.quantile(0.95)),
    }


def group_metrics(frame: pd.DataFrame, key: str) -> list[dict]:
    out = []
    for k, g in frame.dropna(subset=["actual"]).groupby(key):
        m = metrics(g)
        out.append({key: k, "n": m["n"], "mae": m["mae"], "rmse": m["rmse"], "bias": m["bias"],
                    "mean_actual": _r(g["actual"].mean()), "mean_forecast": _r(g["forecast"].mean())})
    return out


def by_horizon(frame: pd.DataFrame, width: int = 4) -> list[dict]:
    f = frame.copy()
    f["bucket"] = (f["horizon_h"] // width * width).astype(int)
    rows = group_metrics(f, "bucket")
    for r in rows:
        r["bucket"] = int(r["bucket"])
        r["label"] = f"{r['bucket']}-{r['bucket'] + width}h"
    return rows


def error_histogram(frame: pd.DataFrame, width: int = 500) -> list[dict]:
    e = frame.dropna(subset=["actual"])["error"]
    if e.empty:
        return []
    lo = int(np.floor(e.min() / width) * width)
    hi = int(np.ceil(e.max() / width) * width) + width
    edges = np.arange(lo, hi + 1, width)
    counts, _ = np.histogram(e, bins=edges)
    return [{"start": int(a), "end": int(a + width), "label": f"{int(a)}", "count": int(c)}
            for a, c in zip(edges[:-1], counts)]


def band_quantiles(frame: pd.DataFrame, delivery_date: str, min_days: int = 3,
                   lo: float = 0.05, hi: float = 0.95) -> dict | None:
    """Empirical range for (actual - forecast) used to draw an uncertainty band.

    Only delivery days <= D-2 are used (at the cutoff on D-1, day D-1 is still in progress,
    so its errors are not yet known). If fewer than `min_days` such days exist we fall back
    to the whole period and say so.
    """
    valid = frame.dropna(subset=["actual"])
    limit = (date.fromisoformat(delivery_date) - timedelta(days=2)).isoformat()
    sample, basis = valid[valid["delivery_date"] <= limit], "prior days only"
    if sample["delivery_date"].nunique() < min_days:
        sample, basis = valid, "whole period (too little history before this day)"
    if sample.empty:
        return None
    e = sample["actual"] - sample["forecast"]
    return {"basis": basis, "days": int(sample["delivery_date"].nunique()), "n": int(len(e)),
            "q_lo": _r(e.quantile(lo)), "q_hi": _r(e.quantile(hi)), "level": round(hi - lo, 2)}
