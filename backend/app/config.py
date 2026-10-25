"""Central configuration. Everything can be overridden with environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data"))

# Elexon BMRS endpoints (override ELEXON_BASE / the full URLs if the brief links differ).
ELEXON_BASE = os.getenv("ELEXON_BASE", "https://data.elexon.co.uk/bmrs/api/v1")
ACTUALS_URL = os.getenv("ACTUALS_URL", f"{ELEXON_BASE}/datasets/FUELHH/stream")
FORECAST_URL = os.getenv("FORECAST_URL", f"{ELEXON_BASE}/datasets/WINDFOR/stream")

TZ = "Europe/London"

# Purchase decisions are made in January 2026 (on day D-1) for delivery days 2 Jan - 1 Feb.
DELIVERY_START = "2026-01-02"
DELIVERY_END = "2026-02-01"

# Assumed day-ahead decision cutoff (London time on D-1). Configurable in the UI.
DEFAULT_CUTOFF = os.getenv("DEFAULT_CUTOFF", "09:30")

# Forecasts published more than this many hours before the target are dropped at fetch time.
MAX_HORIZON_H = 72
