from datetime import date, datetime, timezone

import pandas as pd

from app import elexon


class FakeClient:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_fetch_actuals_uses_weekly_wind_query(monkeypatch):
    requests = []

    def fake_get_json(_client, url, params):
        requests.append((url, params))
        return [
            {"fuelType": "WIND", "startTime": "2026-01-14T00:00:00Z", "generation": 1200},
            {"fuelType": "GAS", "startTime": "2026-01-14T00:00:00Z", "generation": 900},
        ]

    monkeypatch.setattr(elexon.httpx, "Client", FakeClient)
    monkeypatch.setattr(elexon, "_get_json", fake_get_json)

    actuals = elexon.fetch_actuals(date(2026, 1, 14), date(2026, 1, 20))

    assert len(requests) == 1
    url, params = requests[0]
    assert url.endswith("/datasets/FUELHH/stream")
    assert params["settlementDateFrom"] == "2026-01-14"
    assert params["settlementDateTo"] == "2026-01-20"
    assert params["fuelType"] == "WIND"
    assert list(actuals["actual"]) == [1200.0]


def test_fetch_forecasts_uses_daily_publish_query(monkeypatch):
    requests = []

    def fake_get_json(_client, url, params):
        requests.append((url, params))
        return [{
            "startTime": "2026-01-14T12:00:00Z",
            "publishTime": "2026-01-14T00:00:00Z",
            "generation": 2500,
        }]

    monkeypatch.setattr(elexon.httpx, "Client", FakeClient)
    monkeypatch.setattr(elexon, "_get_json", fake_get_json)

    forecasts = elexon.fetch_forecasts(
        date(2026, 1, 14),
        date(2026, 1, 14),
        datetime(2026, 1, 14, tzinfo=timezone.utc),
        datetime(2026, 1, 15, tzinfo=timezone.utc),
    )

    assert len(requests) == 1
    url, params = requests[0]
    assert url.endswith("/datasets/WINDFOR/stream")
    assert params["publishDateTimeFrom"] == "2026-01-14T00:00:00Z"
    assert params["publishDateTimeTo"] == "2026-01-14T23:59:59Z"
    assert len(forecasts) == 1
    assert forecasts.iloc[0]["generation"] == 2500.0
