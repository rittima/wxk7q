from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json() == {"status": "ok"}


def test_meta_lists_january_delivery_days():
    body = client.get("/api/meta").json()
    assert body["source"] == "synthetic"
    assert body["delivery_dates"][0] == "2026-01-02" and body["delivery_dates"][-1] == "2026-02-01"


def test_forecast_never_uses_forecasts_after_cutoff():
    body = client.get("/api/forecast", params={"delivery_date": "2026-01-15", "cutoff": "09:30"}).json()
    assert body["summary"]["n_points"] == 48
    assert body["summary"]["latest_publish"] <= "2026-01-14T09:30:00Z"
    assert all(p["lower"] <= p["forecast"] <= p["upper"] for p in body["points"])


def test_earlier_cutoff_changes_publish_time():
    a = client.get("/api/forecast", params={"delivery_date": "2026-01-15", "cutoff": "09:30"}).json()
    b = client.get("/api/forecast", params={"delivery_date": "2026-01-15", "cutoff": "06:00"}).json()
    assert b["summary"]["latest_publish"] < a["summary"]["latest_publish"]


def test_accuracy_error_grows_with_horizon():
    body = client.get("/api/accuracy").json()
    h = body["by_horizon"]
    assert h[0]["mae"] < h[-1]["mae"]
    assert body["summary"]["n"] > 1000


def test_validation_and_not_found():
    assert client.get("/api/forecast", params={"delivery_date": "2026-01-15", "cutoff": "9.30"}).status_code == 422
    assert client.get("/api/forecast", params={"delivery_date": "not-a-date"}).status_code == 422
    assert client.get("/api/forecast", params={"delivery_date": "2026-03-01"}).status_code == 404
