"""Glue between cached data and the analysis functions; shapes API responses."""
from datetime import date, timedelta
from functools import lru_cache

import pandas as pd

from . import analysis, config, data


@lru_cache(maxsize=32)
def decision_frame(cutoff: str) -> pd.DataFrame:
    """Decision-time forecast joined with actuals, for every delivery day in scope."""
    fc, act, _ = data.load()
    df = analysis.decision_forecasts(fc, cutoff)
    df = df[df["delivery_date"].between(config.DELIVERY_START, config.DELIVERY_END)]
    return analysis.join_actuals(df, act)


def _records(df: pd.DataFrame) -> list[dict]:
    return df.astype(object).where(df.notna(), None).to_dict("records")


def meta(cutoff: str) -> dict:
    _, _, m = data.load()
    df = decision_frame(cutoff)
    dates = sorted(df["delivery_date"].unique().tolist())
    return {
        "source": m.get("source", "unknown"),
        "fetched_at": m.get("fetched_at"),
        "delivery_dates": dates,
        "default_cutoff": config.DEFAULT_CUTOFF,
        "timezone": config.TZ,
    }


def forecast_view(delivery_date: str, cutoff: str) -> dict:
    df = decision_frame(cutoff)
    day = df[df["delivery_date"] == delivery_date].sort_values("startTime")
    if day.empty:
        raise LookupError(f"No forecast data for {delivery_date}")
    band = analysis.band_quantiles(df, delivery_date)
    day = day.copy()
    if band:
        day["lower"] = (day["forecast"] + band["q_lo"]).clip(lower=0)
        day["upper"] = day["forecast"] + band["q_hi"]
    else:
        day["lower"] = day["upper"] = None
    pts = day[["startTime", "label", "forecast", "actual", "lower", "upper", "horizon_h", "publishTime"]].copy()
    pts["startTime"] = pts["startTime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    pts["publishTime"] = pts["publishTime"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    pts["horizon_h"] = pts["horizon_h"].round(1)
    pts = pts.rename(columns={"startTime": "time", "publishTime": "publish_time"})
    prev = (date.fromisoformat(delivery_date) - timedelta(days=1)).isoformat()
    return {
        "delivery_date": delivery_date,
        "cutoff_local": f"{prev} {cutoff}",
        "points": _records(pts),
        "summary": {
            "n_points": int(len(day)),
            "expected_points": 48,
            "avg_forecast": analysis._r(day["forecast"].mean()),
            "peak_forecast": analysis._r(day["forecast"].max()),
            "min_forecast": analysis._r(day["forecast"].min()),
            "avg_lower": analysis._r(day["lower"].mean()) if band else None,
            "avg_upper": analysis._r(day["upper"].mean()) if band else None,
            "earliest_publish": pts["publish_time"].min(),
            "latest_publish": pts["publish_time"].max(),
            "actuals_available": bool(day["actual"].notna().any()),
        },
        "band": band,
        "day_metrics": analysis.metrics(day),
    }


def accuracy(cutoff: str, date_from: str | None, date_to: str | None) -> dict:
    df = decision_frame(cutoff)
    if date_from:
        df = df[df["delivery_date"] >= date_from]
    if date_to:
        df = df[df["delivery_date"] <= date_to]
    if df.empty:
        raise LookupError("No data in the requested range")
    hours = analysis.group_metrics(df, "hour")
    daily = analysis.group_metrics(df, "delivery_date")
    return {
        "cutoff": cutoff,
        "date_from": df["delivery_date"].min(),
        "date_to": df["delivery_date"].max(),
        "summary": analysis.metrics(df),
        "mean_actual": analysis._r(df["actual"].mean()),
        "by_hour": hours,
        "by_horizon": analysis.by_horizon(df),
        "daily": daily,
        "histogram": analysis.error_histogram(df),
        "horizon_range_h": [analysis._r(df["horizon_h"].min()), analysis._r(df["horizon_h"].max())],
    }
