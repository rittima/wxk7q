import pandas as pd
import pytest

from app import analysis


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make_fc():
    # Target: 15 Jan 2026 12:00 UTC. Cutoff (09:30 London = 09:30 UTC in winter) is 14 Jan 09:30.
    target = ts("2026-01-15 12:00")
    return pd.DataFrame({
        "startTime": [target] * 4,
        "publishTime": [ts("2026-01-13 09:00"), ts("2026-01-14 09:00"),
                        ts("2026-01-14 09:30"), ts("2026-01-14 10:00")],
        "generation": [1000.0, 2000.0, 3000.0, 4000.0],
    })


def test_picks_latest_forecast_at_or_before_cutoff():
    out = analysis.decision_forecasts(make_fc(), "09:30")
    assert len(out) == 1
    assert out.loc[0, "forecast"] == 3000.0          # 09:30 is allowed; 10:00 is hindsight
    assert out.loc[0, "horizon_h"] == pytest.approx(26.5)
    assert out.loc[0, "delivery_date"] == "2026-01-15"


def test_earlier_cutoff_uses_older_forecast():
    out = analysis.decision_forecasts(make_fc(), "09:15")
    assert out.loc[0, "forecast"] == 2000.0


def test_no_forecast_before_cutoff_drops_target():
    out = analysis.decision_forecasts(make_fc(), "08:00")
    assert out.loc[0, "forecast"] == 1000.0
    assert analysis.decision_forecasts(make_fc().iloc[2:], "08:00").empty


def test_bad_cutoff_rejected():
    with pytest.raises(ValueError):
        analysis.parse_cutoff("25:00")


def frame(forecast, actual, dates=None):
    n = len(forecast)
    return pd.DataFrame({
        "forecast": forecast, "actual": actual,
        "error": [f - a if a == a else float("nan") for f, a in zip(forecast, actual)],
        "delivery_date": dates or ["2026-01-02"] * n, "horizon_h": [20.0] * n, "hour": [0] * n,
    })


def test_metrics_sign_and_values():
    m = analysis.metrics(frame([110, 90, 100], [100, 100, 100]))
    assert m["n"] == 3
    assert m["mae"] == pytest.approx(6.7, abs=0.05)
    assert m["bias"] == 0.0                           # +10 and -10 cancel
    assert m["rmse"] == pytest.approx(8.2, abs=0.05)


def test_metrics_ignores_missing_actuals():
    m = analysis.metrics(frame([100, 200], [90, float("nan")]))
    assert m["n"] == 1 and m["bias"] == 10.0


def test_band_uses_only_days_up_to_d_minus_2():
    dates = [f"2026-01-{d:02d}" for d in range(2, 12)]
    df = frame([100.0] * 10, [100.0 + i for i in range(10)], dates)
    band = analysis.band_quantiles(df, "2026-01-08", min_days=3)
    assert band["basis"] == "prior days only"
    assert band["days"] == 5                          # 2..6 Jan; 7 Jan is D-1 and not yet known


def test_band_falls_back_when_history_short():
    df = frame([100.0] * 4, [100.0, 101.0, 102.0, 103.0], ["2026-01-02", "2026-01-03", "2026-01-04", "2026-01-05"])
    band = analysis.band_quantiles(df, "2026-01-03", min_days=3)
    assert band["basis"].startswith("whole period")


def test_histogram_counts_all_points():
    df = frame([100, 700, 150, 90], [100, 100, 100, 100])
    assert sum(b["count"] for b in analysis.error_histogram(df)) == 4
