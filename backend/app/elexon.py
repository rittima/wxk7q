"""Thin client for the Elexon BMRS API (actual wind generation and wind forecasts)."""
import time
from datetime import date, datetime, timedelta, timezone

import httpx
import pandas as pd

from . import config


def _get_json(client: httpx.Client, url: str, params: dict, retries: int = 4):
    for attempt in range(retries):
        try:
            resp = client.get(url, params=params, timeout=60)
            resp.raise_for_status()
            body = resp.json()
            return body["data"] if isinstance(body, dict) and "data" in body else body
        except (httpx.HTTPError, ValueError):
            if attempt == retries - 1:
                raise
            time.sleep(2**attempt)


def _chunks(start: date, end: date, days: int):
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=days - 1), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def fetch_actuals(start: date, end: date) -> pd.DataFrame:
    """National wind generation (MW) per half hour: columns startTime (UTC), actual."""
    rows = []
    with httpx.Client() as client:
        for a, b in _chunks(start, end, 7):
            params = {
                "settlementDateFrom": a.isoformat(),
                "settlementDateTo": b.isoformat(),
                "fuelType": "WIND",
                "format": "json",
            }
            rows += _get_json(client, config.ACTUALS_URL, params)
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"].copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["actual"] = df["generation"].astype(float)
    return (
        df.sort_values("startTime")
        .drop_duplicates("startTime", keep="last")[["startTime", "actual"]]
        .reset_index(drop=True)
    )


def fetch_forecasts(pub_from: date, pub_to: date, target_from: datetime, target_to: datetime) -> pd.DataFrame:
    """Wind forecasts: columns startTime, publishTime (UTC), generation (MW)."""
    rows = []
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    with httpx.Client() as client:
        for a, b in _chunks(pub_from, pub_to, 1):
            start = datetime(a.year, a.month, a.day, tzinfo=timezone.utc)
            params = {
                "publishDateTimeFrom": start.strftime(fmt),
                "publishDateTimeTo": (start + timedelta(days=1) - timedelta(seconds=1)).strftime(fmt),
                "format": "json",
            }
            rows += _get_json(client, config.FORECAST_URL, params)
    df = pd.DataFrame(rows)
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df["generation"] = df["generation"].astype(float)
    horizon = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    keep = (
        (df["startTime"] >= target_from)
        & (df["startTime"] < target_to)
        & (horizon >= 0)
        & (horizon <= config.MAX_HORIZON_H)
    )
    return (
        df[keep][["startTime", "publishTime", "generation"]]
        .drop_duplicates(["startTime", "publishTime"], keep="last")
        .sort_values(["publishTime", "startTime"])
        .reset_index(drop=True)
    )
