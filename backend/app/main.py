"""FastAPI app: JSON API under /api, and the built React app (if present) at /."""
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, service

app = FastAPI(title="Wind forecast desk API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

_CUTOFF_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _cutoff(value: str) -> str:
    if not _CUTOFF_RE.match(value):
        raise HTTPException(422, "cutoff must be HH:MM (London time, on the day before delivery)")
    return value


def _date(value: str | None, name: str) -> str | None:
    if value is not None and not _DATE_RE.match(value):
        raise HTTPException(422, f"{name} must be YYYY-MM-DD")
    return value


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/meta")
def meta(cutoff: str = config.DEFAULT_CUTOFF):
    try:
        return service.meta(_cutoff(cutoff))
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@app.get("/api/forecast")
def forecast(delivery_date: str = Query(...), cutoff: str = config.DEFAULT_CUTOFF):
    _date(delivery_date, "delivery_date")
    try:
        return service.forecast_view(delivery_date, _cutoff(cutoff))
    except LookupError as e:
        raise HTTPException(404, str(e))
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


@app.get("/api/accuracy")
def accuracy(cutoff: str = config.DEFAULT_CUTOFF, date_from: str | None = None, date_to: str | None = None):
    _date(date_from, "date_from"), _date(date_to, "date_to")
    try:
        return service.accuracy(_cutoff(cutoff), date_from, date_to)
    except LookupError as e:
        raise HTTPException(404, str(e))
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))


# Serve the React build when it exists (Docker image copies it to ./static).
_static = Path(__file__).resolve().parent.parent / "static"
if _static.is_dir():
    app.mount("/", StaticFiles(directory=_static, html=True), name="web")
