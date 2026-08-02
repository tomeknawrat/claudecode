"""Tests for the Garmin MCP server tools, helpers, and validation.

Run with:  pytest   (asyncio_mode=auto is configured in pyproject.toml)
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from garmin_mcp import client as client_mod
from garmin_mcp import server as srv
from garmin_mcp.server import (
    ActivityInput,
    DateInput,
    DateRangeInput,
    ListActivitiesInput,
    WeeklySummaryInput,
    garmin_get_activity,
    garmin_get_body_battery,
    garmin_get_body_composition,
    garmin_get_daily_summary,
    garmin_get_heart_rate,
    garmin_get_hrv,
    garmin_get_profile,
    garmin_get_sleep,
    garmin_get_steps,
    garmin_get_stress,
    garmin_get_training_readiness,
    garmin_get_training_status,
    garmin_get_vo2max,
    garmin_get_weekly_summary,
    garmin_list_activities,
)

# ---------------------------------------------------------------------------
# Pure helper functions
# ---------------------------------------------------------------------------


def test_num_formats_and_handles_none():
    assert srv._num(None) == "n/a"
    assert srv._num(1234) == "1,234"
    assert srv._num(1.2345, 2) == "1.23"
    assert srv._num("abc") == "abc"


def test_mins_renders_duration():
    assert srv._mins(None) == "n/a"
    assert srv._mins(3661) == "1:01:01"
    assert srv._mins(0) == "0:00:00"


def test_validate_date_accepts_iso_and_rejects_bad():
    assert srv._validate_date("2026-07-30") == "2026-07-30"
    with pytest.raises(ValueError):
        srv._validate_date("30/07/2026")
    with pytest.raises(ValueError):
        srv._validate_date("not-a-date")


def test_check_range_orders_and_bounds():
    srv._check_range("2026-07-01", "2026-07-08")  # ok
    with pytest.raises(ValueError):
        srv._check_range("2026-07-08", "2026-07-01")  # reversed
    with pytest.raises(ValueError):
        srv._check_range("2020-01-01", "2026-01-01")  # too large


def test_first_and_first_val_unwrap():
    assert srv._first([{"a": 1}]) == {"a": 1}
    assert srv._first([]) == {}
    assert srv._first({"a": 1}) == {"a": 1}
    assert srv._first("x") == {}
    assert srv._first_val({"deviceX": {"k": 1}}) == {"k": 1}
    assert srv._first_val({}) == {}
    assert srv._first_val(None) == {}


def test_clean_formats_enum_tokens():
    assert srv._clean("READY_TO_TRAIN") == "Ready to train"
    assert srv._clean(None) == "n/a"


def test_aggregate_days_totals_and_best_day():
    summaries = [
        {"calendarDate": "2026-07-01", "totalSteps": 1000, "totalDistanceMeters": 700,
         "totalKilocalories": 2000, "activeKilocalories": 500, "floorsAscended": 1,
         "restingHeartRate": 50, "averageStressLevel": 30,
         "moderateIntensityMinutes": 20, "vigorousIntensityMinutes": 10},
        {"calendarDate": "2026-07-02", "totalSteps": 3000, "totalDistanceMeters": 2100,
         "totalKilocalories": 2200, "activeKilocalories": 700, "floorsAscended": 3,
         "restingHeartRate": 52, "averageStressLevel": 40,
         "moderateIntensityMinutes": 40, "vigorousIntensityMinutes": 20},
    ]
    agg = srv._aggregate_days("2026-07-01", "2026-07-02", 2, summaries)
    assert agg["total_steps"] == 4000
    assert agg["avg_steps_per_day"] == 2000
    assert agg["days_with_data"] == 2
    assert agg["avg_resting_hr"] == 51
    assert agg["total_intensity_minutes"] == 90
    assert agg["best_day"] == {"date": "2026-07-02", "steps": 3000}


def test_aggregate_days_empty():
    agg = srv._aggregate_days("2026-07-01", "2026-07-02", 2, [])
    assert agg["days_with_data"] == 0
    assert agg["total_steps"] == 0
    assert agg["avg_resting_hr"] is None
    assert agg["best_day"] is None


# ---------------------------------------------------------------------------
# Input validation (Pydantic models)
# ---------------------------------------------------------------------------


def test_date_input_rejects_bad_date():
    with pytest.raises(ValidationError):
        DateInput(cdate="nonsense")


def test_weekly_summary_days_bounds():
    with pytest.raises(ValidationError):
        WeeklySummaryInput(days=0)
    with pytest.raises(ValidationError):
        WeeklySummaryInput(days=99)


def test_list_activities_limit_bounds():
    with pytest.raises(ValidationError):
        ListActivitiesInput(limit=0)
    with pytest.raises(ValidationError):
        ListActivitiesInput(limit=1000)


def test_models_forbid_extra_fields():
    with pytest.raises(ValidationError):
        DateInput(cdate="2026-07-30", bogus=1)


# ---------------------------------------------------------------------------
# Tools — markdown output
# ---------------------------------------------------------------------------


async def test_profile(patched):
    out = await garmin_get_profile(srv._Base())
    assert "Test User" in out and "metric" in out


async def test_list_activities_recent(patched):
    out = await garmin_list_activities(ListActivitiesInput(limit=3))
    assert "Activities" in out and "ID" in out


async def test_list_activities_requires_both_dates(patched):
    out = await garmin_list_activities(ListActivitiesInput(start_date="2026-07-01"))
    assert out.startswith("Error:") and "both" in out


async def test_list_activities_by_date_filters_type(patched):
    out = await garmin_list_activities(
        ListActivitiesInput(start_date="2026-07-01", end_date="2026-07-31",
                            activity_type="running", response_format="json")
    )
    data = json.loads(out)
    assert data and all(a["activityType"]["typeKey"] == "running" for a in data)


async def test_get_activity_strips_heavy_arrays(patched):
    out = await garmin_get_activity(
        ActivityInput(activity_id="1000", include_splits=True,
                      include_weather=True, response_format="json")
    )
    data = json.loads(out)
    assert "activityDetailMetrics" not in data
    assert "geoPolylineDTO" not in data
    assert "summaryDTO" in data
    assert data["_splits"] and data["_weather"]


async def test_daily_summary(patched):
    out = await garmin_get_daily_summary(DateInput(cdate="2026-07-30"))
    assert "Daily summary" in out and "Steps" in out


async def test_heart_rate(patched):
    out = await garmin_get_heart_rate(DateInput(cdate="2026-07-30"))
    assert "Resting HR" in out


async def test_sleep(patched):
    out = await garmin_get_sleep(DateInput(cdate="2026-07-30"))
    assert "Sleep score" in out and "7:20:00" in out


async def test_stress(patched):
    out = await garmin_get_stress(DateInput(cdate="2026-07-30"))
    assert "Avg stress" in out


async def test_body_battery(patched):
    out = await garmin_get_body_battery(
        DateRangeInput(start_date="2026-07-28", end_date="2026-07-30")
    )
    assert "Body Battery" in out and "Range" in out


async def test_steps(patched):
    out = await garmin_get_steps(DateInput(cdate="2026-07-30"))
    assert "Total steps" in out and "1,500" in out


async def test_body_composition(patched):
    out = await garmin_get_body_composition(
        DateRangeInput(start_date="2026-07-01", end_date="2026-07-30")
    )
    assert "72.50 kg" in out and "Body fat" in out


async def test_training_readiness(patched):
    out = await garmin_get_training_readiness(DateInput(cdate="2026-07-30"))
    assert "Training Readiness" in out and "78/100" in out


async def test_training_status(patched):
    out = await garmin_get_training_status(DateInput(cdate="2026-07-30"))
    assert "Training Status" in out and "Productive" in out and "250–450" in out


async def test_hrv(patched):
    out = await garmin_get_hrv(DateInput(cdate="2026-07-30"))
    assert "HRV" in out and "55 ms" in out


async def test_vo2max(patched):
    out = await garmin_get_vo2max(DateInput(cdate="2026-07-30"))
    assert "VO2 max" in out and "52.4" in out and "31 years" in out


async def test_weekly_summary_aggregates(patched):
    out = await garmin_get_weekly_summary(
        WeeklySummaryInput(end_date="2026-07-03", days=3, response_format="json")
    )
    data = json.loads(out)
    # days 01,02,03 -> steps 1000,2000,3000
    assert data["days_with_data"] == 3
    assert data["total_steps"] == 6000
    assert data["best_day"]["date"] == "2026-07-03"


# ---------------------------------------------------------------------------
# Empty-data and error handling
# ---------------------------------------------------------------------------


async def test_hrv_no_data(patched):
    patched.get_hrv_data = lambda cdate: None
    out = await garmin_get_hrv(DateInput(cdate="2026-07-30"))
    assert "No HRV data" in out


async def test_training_status_no_data(patched):
    patched.get_training_status = lambda cdate: {}
    out = await garmin_get_training_status(DateInput(cdate="2026-07-30"))
    assert "No training status data" in out


async def test_weekly_summary_skips_failing_days(patched):
    def flaky(cdate):
        if cdate.endswith("-02"):
            raise RuntimeError("no data for this day")
        day = int(cdate.split("-")[-1])
        return {"calendarDate": cdate, "totalSteps": 1000 * day}

    patched.get_user_summary = flaky
    out = await garmin_get_weekly_summary(
        WeeklySummaryInput(end_date="2026-07-03", days=3, response_format="json")
    )
    data = json.loads(out)
    assert data["days_with_data"] == 2  # day 02 skipped
    assert data["total_steps"] == 4000  # 1000 + 3000


async def test_tool_returns_error_on_api_failure(monkeypatch):
    def boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(srv.client, "get_api", boom)
    out = await garmin_get_daily_summary(DateInput(cdate="2026-07-30"))
    assert out.startswith("Error:")


async def test_tool_returns_error_on_auth_failure(monkeypatch):
    def auth_fail():
        raise client_mod.GarminAuthError("bad credentials")

    monkeypatch.setattr(srv.client, "get_api", auth_fail)
    out = await garmin_get_profile(srv._Base())
    assert out.startswith("Error:") and "authentication failed" in out


# ---------------------------------------------------------------------------
# Registration sanity
# ---------------------------------------------------------------------------


async def test_all_tools_registered():
    tools = await srv.mcp.list_tools()
    names = {t.name for t in tools}
    expected = {
        "garmin_get_profile", "garmin_list_activities", "garmin_get_activity",
        "garmin_get_daily_summary", "garmin_get_heart_rate", "garmin_get_sleep",
        "garmin_get_stress", "garmin_get_body_battery", "garmin_get_steps",
        "garmin_get_body_composition", "garmin_get_training_readiness",
        "garmin_get_training_status", "garmin_get_hrv", "garmin_get_vo2max",
        "garmin_get_weekly_summary",
    }
    assert expected <= names
    # Every tool must be read-only.
    for t in tools:
        assert t.annotations and t.annotations.readOnlyHint is True
