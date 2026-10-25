"""Loads the cached CSVs produced by scripts/build_cache.py."""
import json
from functools import lru_cache

import pandas as pd

from . import config


@lru_cache(maxsize=1)
def load():
    d = config.DATA_DIR
    fc_path, act_path, meta_path = d / "wind_forecasts.csv.gz", d / "wind_actuals.csv", d / "meta.json"
    if not (fc_path.exists() and act_path.exists()):
        raise FileNotFoundError(
            f"No cached data in {d}. Run `python -m scripts.build_cache` (or add --synthetic for demo data)."
        )
    fc = pd.read_csv(fc_path)
    act = pd.read_csv(act_path)
    for df in (fc, act):
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"source": "unknown"}
    return fc, act, meta
