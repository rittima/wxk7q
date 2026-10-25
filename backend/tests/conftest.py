import os
import sys
import tempfile
from pathlib import Path

# Point the app at a throwaway synthetic dataset *before* it is imported.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
_tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = _tmp

from app import config  # noqa: E402
from scripts import build_cache  # noqa: E402

fc, act = build_cache.synthetic()
fc.to_csv(Path(_tmp) / "wind_forecasts.csv.gz", index=False, compression="gzip")
act.to_csv(Path(_tmp) / "wind_actuals.csv", index=False)
(Path(_tmp) / "meta.json").write_text('{"source": "synthetic"}')
