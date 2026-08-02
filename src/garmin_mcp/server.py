#!/usr/bin/env python3
"""MCP server for Garmin Connect.

Exposes an authenticated Garmin Connect account to an MCP client (such as
Claude) as a set of read-only tools covering four domains:

- **Activities**   -- runs, rides, swims, etc. (list + per-activity detail)
- **Health & wellness** -- steps, heart rate, sleep, stress, Body Battery
- **Body composition** -- weight, body-fat %, BMI, muscle mass
- **Summaries**    -- daily/aggregate wellness statistics

Data is read through the unofficial ``garminconnect`` library, which talks
to the same private API used by the Garmin Connect web app. See ``client.py``
for authentication details.

All tools are read-only: this server never modifies Garmin data.
"""

from __future__ import annotations

import asyncio
import json
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .client import GarminAuthError, client

# ---------------------------------------------------------------------------
# Server setup
# ---------------------------------------------------------------------------

mcp = FastMCP("garmin_mcp")

_DATE_FMT = "%Y-%m-%d"
_MAX_RANGE_DAYS = 366  # guard against accidentally huge multi-year pulls

# Read-only annotations shared by every tool in this server.
_READ_ONLY = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}


class ResponseFormat(str, Enum):
    """Output format for tool responses."""

    MARKDOWN = "markdown"
    JSON = "json"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _today() -> str:
    return date.today().strftime(_DATE_FMT)


def _validate_date(value: str) -> str:
    """Validate a ``YYYY-MM-DD`` date string, returning it normalized."""
    try:
        return datetime.strptime(value.strip(), _DATE_FMT).strftime(_DATE_FMT)
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            f"Invalid date '{value}'. Use ISO format YYYY-MM-DD (e.g. 2024-05-17)."
        ) from exc


def _check_range(start: str, end: str) -> None:
    """Ensure a start/end date range is ordered and not absurdly large."""
    s = datetime.strptime(start, _DATE_FMT).date()
    e = datetime.strptime(end, _DATE_FMT).date()
    if e < s:
        raise ValueError(f"end_date ({end}) must not be before start_date ({start}).")
    if (e - s).days > _MAX_RANGE_DAYS:
        raise ValueError(
            f"Date range too large ({(e - s).days} days). "
            f"Keep it within {_MAX_RANGE_DAYS} days per request."
        )


async def _call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Run a blocking ``garminconnect`` call in a worker thread.

    ``garminconnect`` is synchronous, so every network call is offloaded to a
    thread to avoid blocking the event loop. Authentication happens lazily on
    the first call.
    """
    api = await asyncio.to_thread(client.get_api)
    return await asyncio.to_thread(fn, api, *args, **kwargs)


def _handle_error(e: Exception) -> str:
    """Format an exception into an actionable, agent-friendly error string."""
    if isinstance(e, GarminAuthError):
        return f"Error: Garmin authentication failed. {e}"
    if isinstance(e, ValueError):
        return f"Error: {e}"
    name = type(e).__name__
    if "TooManyRequests" in name or "429" in str(e):
        return (
            "Error: Garmin rate limit hit (too many requests). "
            "Wait a bit before retrying."
        )
    if "Authentication" in name:
        return (
            "Error: Garmin authentication failed. Check GARMIN_EMAIL / "
            "GARMIN_PASSWORD (and GARMIN_MFA_CODE if 2FA is on). "
            f"Details: {e}"
        )
    if "Connection" in name:
        return f"Error: Could not reach Garmin Connect. {e}"
    return f"Error: Unexpected {name}: {e}"


def _num(value: Any, digits: int = 0) -> str:
    """Format a possibly-missing number for markdown, or 'n/a'."""
    if value is None:
        return "n/a"
    try:
        if digits:
            return f"{float(value):,.{digits}f}"
        return f"{float(value):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def _mins(seconds: Any) -> str:
    """Render a duration given in seconds as ``H:MM:SS`` (or 'n/a')."""
    if seconds is None:
        return "n/a"
    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return str(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _dump(data: Any) -> str:
    """Serialize structured data to indented JSON (dates handled)."""
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def _first(data: Any) -> dict:
    """Unwrap a single-item list; several Garmin endpoints wrap a dict in a list."""
    if isinstance(data, list):
        return data[0] if data else {}
    return data if isinstance(data, dict) else {}


def _first_val(mapping: Any) -> dict:
    """Return the first value of a dict keyed by a dynamic id (e.g. a device id).

    Several Garmin endpoints nest the data-of-interest under a per-device key
    (the watch's ID), so callers can't know the key ahead of time.
    """
    if isinstance(mapping, dict) and mapping:
        first = next(iter(mapping.values()))
        return first if isinstance(first, dict) else {}
    return {}


def _format(data: Any, fmt: ResponseFormat, markdown_fn: Callable[[Any], str]) -> str:
    """Dispatch to JSON dump or a markdown formatter based on ``fmt``."""
    if fmt == ResponseFormat.JSON:
        return _dump(data)
    return markdown_fn(data)


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class _Base(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' (human-readable summary) or "
        "'json' (complete structured data).",
    )


class DateInput(_Base):
    """A single calendar day."""

    cdate: str = Field(
        default_factory=_today,
        description="Calendar day in ISO format YYYY-MM-DD (default: today).",
    )

    @field_validator("cdate")
    @classmethod
    def _v(cls, v: str) -> str:
        return _validate_date(v)


class DateRangeInput(_Base):
    """A start/end calendar-day range (inclusive)."""

    start_date: str = Field(
        ..., description="Range start day, ISO format YYYY-MM-DD."
    )
    end_date: str = Field(
        default_factory=_today,
        description="Range end day, ISO format YYYY-MM-DD (default: today).",
    )

    @field_validator("start_date", "end_date")
    @classmethod
    def _v(cls, v: str) -> str:
        return _validate_date(v)


class ListActivitiesInput(_Base):
    """Filter/paginate the activity list."""

    limit: int = Field(
        default=10, description="Maximum activities to return.", ge=1, le=100
    )
    start: int = Field(
        default=0,
        description="Number of most-recent activities to skip (pagination offset).",
        ge=0,
    )
    start_date: Optional[str] = Field(
        default=None,
        description="Optional lower bound day (YYYY-MM-DD). If set, results are "
        "filtered to activities on/after this day (end_date also required).",
    )
    end_date: Optional[str] = Field(
        default=None,
        description="Optional upper bound day (YYYY-MM-DD). Used with start_date.",
    )
    activity_type: Optional[str] = Field(
        default=None,
        description="Optional type filter, e.g. 'running', 'cycling', 'swimming', "
        "'walking', 'hiking', 'strength_training'. Only applied with a date range.",
    )

    @field_validator("start_date", "end_date")
    @classmethod
    def _v(cls, v: Optional[str]) -> Optional[str]:
        return _validate_date(v) if v else v


class ActivityInput(_Base):
    """Reference a single activity by its ID."""

    activity_id: str = Field(
        ...,
        description="Garmin activity ID (the numeric 'activityId' from "
        "garmin_list_activities, e.g. '1234567890').",
        min_length=1,
    )
    include_splits: bool = Field(
        default=False, description="Include per-lap/split breakdown if available."
    )
    include_weather: bool = Field(
        default=False, description="Include weather conditions if available."
    )


class WeeklySummaryInput(_Base):
    """Aggregate daily wellness stats over a trailing window of days."""

    end_date: str = Field(
        default_factory=_today,
        description="Last day of the window, ISO format YYYY-MM-DD (default: today).",
    )
    days: int = Field(
        default=7,
        description="Number of days to aggregate, ending on end_date (7 = one week).",
        ge=1,
        le=31,
    )

    @field_validator("end_date")
    @classmethod
    def _v(cls, v: str) -> str:
        return _validate_date(v)


# ---------------------------------------------------------------------------
# Markdown formatters
# ---------------------------------------------------------------------------


def _md_activities(items: list) -> str:
    if not items:
        return "No activities found for the given criteria."
    lines = [f"# Activities ({len(items)})", ""]
    for a in items:
        name = a.get("activityName") or "Unnamed activity"
        atype = (a.get("activityType") or {}).get("typeKey", "unknown")
        aid = a.get("activityId")
        start = a.get("startTimeLocal") or a.get("startTimeGMT") or "?"
        dist_km = (a.get("distance") or 0) / 1000.0
        lines.append(f"## {name}  ({atype})")
        lines.append(f"- **ID**: {aid}")
        lines.append(f"- **Start**: {start}")
        if a.get("distance"):
            lines.append(f"- **Distance**: {dist_km:,.2f} km")
        lines.append(f"- **Duration**: {_mins(a.get('duration'))}")
        if a.get("averageHR"):
            lines.append(
                f"- **Heart rate**: avg {_num(a.get('averageHR'))} / "
                f"max {_num(a.get('maxHR'))} bpm"
            )
        if a.get("calories"):
            lines.append(f"- **Calories**: {_num(a.get('calories'))} kcal")
        if a.get("elevationGain"):
            lines.append(f"- **Elevation gain**: {_num(a.get('elevationGain'))} m")
        lines.append("")
    return "\n".join(lines)


def _md_activity(data: dict) -> str:
    summary = data.get("summaryDTO", {}) if isinstance(data, dict) else {}
    dto = data.get("activityDTO") if isinstance(data, dict) else None
    name = (dto or {}).get("activityName") or data.get("activityName") or "Activity"
    lines = [f"# {name}", ""]
    if summary:
        dist = summary.get("distance")
        lines.append(f"- **Distance**: {_num(dist and dist / 1000.0, 2)} km")
        lines.append(f"- **Duration**: {_mins(summary.get('duration'))}")
        lines.append(f"- **Moving time**: {_mins(summary.get('movingDuration'))}")
        lines.append(f"- **Avg speed**: {_num(summary.get('averageSpeed'), 2)} m/s")
        lines.append(
            f"- **Heart rate**: avg {_num(summary.get('averageHR'))} / "
            f"max {_num(summary.get('maxHR'))} bpm"
        )
        lines.append(f"- **Calories**: {_num(summary.get('calories'))} kcal")
        lines.append(f"- **Elevation gain**: {_num(summary.get('elevationGain'))} m")
        if summary.get("averagePower") is not None:
            lines.append(f"- **Avg power**: {_num(summary.get('averagePower'))} W")
    if data.get("_splits"):
        lines.append("")
        lines.append(f"## Splits ({len(data['_splits'])})")
        for i, sp in enumerate(data["_splits"], 1):
            d = (sp.get("distance") or 0) / 1000.0
            lines.append(
                f"{i}. {d:,.2f} km in {_mins(sp.get('duration'))} "
                f"(avg HR {_num(sp.get('averageHR'))})"
            )
    if data.get("_weather"):
        w = data["_weather"]
        lines.append("")
        lines.append("## Weather")
        lines.append(f"- **Temp**: {_num(w.get('temp'))}°")
        lines.append(f"- **Conditions**: {w.get('weatherTypeDTO', {}).get('desc', 'n/a')}")
    return "\n".join(lines)


def _md_daily_summary(d: dict) -> str:
    day = d.get("calendarDate", "?")
    lines = [f"# Daily summary — {day}", ""]
    lines.append(f"- **Steps**: {_num(d.get('totalSteps'))} "
                 f"(goal {_num(d.get('dailyStepGoal'))})")
    lines.append(f"- **Distance**: {_num((d.get('totalDistanceMeters') or 0) / 1000.0, 2)} km")
    lines.append(f"- **Floors climbed**: {_num(d.get('floorsAscended'))}")
    lines.append(f"- **Calories**: {_num(d.get('totalKilocalories'))} kcal "
                 f"(active {_num(d.get('activeKilocalories'))})")
    lines.append(f"- **Resting HR**: {_num(d.get('restingHeartRate'))} bpm")
    lines.append(f"- **Min/Max HR**: {_num(d.get('minHeartRate'))} / "
                 f"{_num(d.get('maxHeartRate'))} bpm")
    lines.append(f"- **Stress (avg)**: {_num(d.get('averageStressLevel'))}")
    lines.append(f"- **Body Battery**: {_num(d.get('bodyBatteryMostRecentValue'))} "
                 f"(range {_num(d.get('bodyBatteryLowestValue'))}–"
                 f"{_num(d.get('bodyBatteryHighestValue'))})")
    lines.append(f"- **Intensity minutes**: moderate {_num(d.get('moderateIntensityMinutes'))}, "
                 f"vigorous {_num(d.get('vigorousIntensityMinutes'))}")
    lines.append(f"- **SpO2 (avg)**: {_num(d.get('averageSpo2'))}%")
    return "\n".join(lines)


def _md_heart_rate(d: dict) -> str:
    day = d.get("calendarDate", "?")
    values = d.get("heartRateValues") or []
    lines = [f"# Heart rate — {day}", ""]
    lines.append(f"- **Resting HR**: {_num(d.get('restingHeartRate'))} bpm")
    lines.append(f"- **Min / Max HR**: {_num(d.get('minHeartRate'))} / "
                 f"{_num(d.get('maxHeartRate'))} bpm")
    lines.append(f"- **7-day avg resting HR**: {_num(d.get('lastSevenDaysAvgRestingHeartRate'))} bpm")
    lines.append(f"- **Intraday samples**: {len(values)} "
                 "(use json format for the full time series)")
    return "\n".join(lines)


def _md_sleep(d: dict) -> str:
    dto = d.get("dailySleepDTO", {}) if isinstance(d, dict) else {}
    day = dto.get("calendarDate", "?")
    lines = [f"# Sleep — {day}", ""]
    lines.append(f"- **Total sleep**: {_mins(dto.get('sleepTimeSeconds'))}")
    lines.append(f"- **Deep**: {_mins(dto.get('deepSleepSeconds'))}")
    lines.append(f"- **Light**: {_mins(dto.get('lightSleepSeconds'))}")
    lines.append(f"- **REM**: {_mins(dto.get('remSleepSeconds'))}")
    lines.append(f"- **Awake**: {_mins(dto.get('awakeSleepSeconds'))}")
    scores = dto.get("sleepScores") or {}
    overall = (scores.get("overall") or {}).get("value")
    lines.append(f"- **Sleep score**: {_num(overall)}")
    if d.get("avgOvernightHrv") is not None:
        lines.append(f"- **Overnight HRV (avg)**: {_num(d.get('avgOvernightHrv'))} ms")
    if d.get("restingHeartRate") is not None:
        lines.append(f"- **Resting HR**: {_num(d.get('restingHeartRate'))} bpm")
    return "\n".join(lines)


def _md_stress(d: dict) -> str:
    day = d.get("calendarDate", "?")
    lines = [f"# Stress — {day}", ""]
    lines.append(f"- **Avg stress**: {_num(d.get('avgStressLevel'))}")
    lines.append(f"- **Max stress**: {_num(d.get('maxStressLevel'))}")
    lines.append(f"- **Rest**: {_mins((d.get('restStressDuration') or 0))}")
    lines.append(f"- **Low**: {_mins((d.get('lowStressDuration') or 0))}")
    lines.append(f"- **Medium**: {_mins((d.get('mediumStressDuration') or 0))}")
    lines.append(f"- **High**: {_mins((d.get('highStressDuration') or 0))}")
    return "\n".join(lines)


def _md_body_battery(items: list) -> str:
    if not items:
        return "No Body Battery data found for the given range."
    lines = ["# Body Battery", ""]
    for entry in items:
        day = entry.get("date", "?")
        charged = entry.get("charged")
        drained = entry.get("drained")
        levels = entry.get("bodyBatteryValuesArray") or []
        vals = [p[1] for p in levels if isinstance(p, (list, tuple)) and len(p) > 1]
        lo = min(vals) if vals else None
        hi = max(vals) if vals else None
        lines.append(f"## {day}")
        lines.append(f"- **Charged**: {_num(charged)}  |  **Drained**: {_num(drained)}")
        lines.append(f"- **Range**: {_num(lo)}–{_num(hi)}")
        lines.append("")
    return "\n".join(lines)


def _md_body_composition(d: dict) -> str:
    total = d.get("totalAverage") or {}
    entries = d.get("dateWeightList") or []
    lines = ["# Body composition", ""]
    if total:
        w = total.get("weight")
        lines.append("## Average over range")
        lines.append(f"- **Weight**: {_num(w and w / 1000.0, 2)} kg")
        lines.append(f"- **Body fat**: {_num(total.get('bodyFat'), 1)} %")
        lines.append(f"- **BMI**: {_num(total.get('bmi'), 1)}")
        lines.append(f"- **Muscle mass**: {_num((total.get('muscleMass') or 0) / 1000.0, 2)} kg")
        lines.append(f"- **Body water**: {_num(total.get('bodyWater'), 1)} %")
        lines.append("")
    if entries:
        lines.append(f"## Measurements ({len(entries)})")
        for e in entries:
            ts = e.get("date")
            when = (
                datetime.utcfromtimestamp(ts / 1000).strftime(_DATE_FMT)
                if isinstance(ts, (int, float))
                else ts
            )
            w = e.get("weight")
            lines.append(
                f"- {when}: {_num(w and w / 1000.0, 2)} kg, "
                f"fat {_num(e.get('bodyFat'), 1)} %, BMI {_num(e.get('bmi'), 1)}"
            )
    if not total and not entries:
        return "No body composition measurements found for the given range."
    return "\n".join(lines)


def _md_steps(items: list) -> str:
    if not items:
        return "No intraday step data found for this day."
    total = sum(i.get("steps", 0) or 0 for i in items)
    lines = ["# Intraday steps", ""]
    lines.append(f"- **Total steps**: {_num(total)}")
    lines.append(f"- **Intervals**: {len(items)} (15-min buckets; json for full series)")
    # Highlight the most active interval.
    peak = max(items, key=lambda i: i.get("steps", 0) or 0, default=None)
    if peak:
        lines.append(
            f"- **Peak interval**: {_num(peak.get('steps'))} steps around "
            f"{peak.get('startGMT', '?')}"
        )
    return "\n".join(lines)


def _md_profile(d: dict) -> str:
    lines = ["# Garmin profile", ""]
    lines.append(f"- **Name**: {d.get('fullName', 'n/a')}")
    lines.append(f"- **Username**: {d.get('userName', 'n/a')}")
    lines.append(f"- **Unit system**: {d.get('unitSystem', 'n/a')}")
    return "\n".join(lines)


def _clean(text: Any) -> str:
    """Turn a Garmin enum-style token (e.g. 'BALANCED_LOW') into readable text."""
    if text is None:
        return "n/a"
    return str(text).replace("_", " ").capitalize()


def _md_training_readiness(d: dict) -> str:
    d = _first(d)
    lines = ["# Training Readiness", ""]
    lines.append(f"- **Score**: {_num(d.get('score'))}/100  ({_clean(d.get('level'))})")
    fb = d.get("feedbackLong") or d.get("feedbackShort")
    if fb:
        lines.append(f"- **Feedback**: {_clean(fb)}")
    lines.append(f"- **Sleep score**: {_num(d.get('sleepScore'))} "
                 f"({_clean(d.get('sleepScoreFactorFeedback'))})")
    if d.get("recoveryTime") is not None:
        lines.append(f"- **Recovery time remaining**: {_num(d.get('recoveryTime'))} min")
    lines.append(f"- **HRV factor**: {_clean(d.get('hrvFactorFeedback'))} "
                 f"(weekly avg {_num(d.get('hrvWeeklyAverage'))} ms)")
    lines.append(f"- **Stress factor**: {_clean(d.get('stressHistoryFactorFeedback'))}")
    lines.append(f"- **Acute load**: {_num(d.get('acuteLoad'))}")
    return "\n".join(lines)


def _md_training_status(d: dict) -> str:
    d = d or {}
    status = _first_val((d.get("mostRecentTrainingStatus") or {}).get("latestTrainingStatusData"))
    balance = _first_val(
        (d.get("mostRecentTrainingLoadBalance") or {}).get("metricsTrainingLoadBalanceDTOMap")
    )
    lines = ["# Training Status", ""]
    lines.append(
        "- **Status**: "
        f"{_clean(status.get('trainingStatusFeedbackPhrase') or status.get('trainingStatusKey'))}"
    )
    lines.append(f"- **Weekly training load**: {_num(status.get('weeklyTrainingLoad'))}")
    if status.get("loadTunnelMin") is not None or status.get("loadTunnelMax") is not None:
        lines.append(
            f"- **Optimal load range**: {_num(status.get('loadTunnelMin'))}"
            f"–{_num(status.get('loadTunnelMax'))}"
        )
    acute = status.get("acuteTrainingLoadDTO") or {}
    acwr = acute.get("acwrPercent") or acute.get("dailyAcuteChronicWorkloadRatio")
    if acwr is not None:
        lines.append(f"- **Acute:chronic load ratio**: {_num(acwr, 2)}")
    if balance:
        lines.append(f"- **Load balance**: {_clean(balance.get('trainingBalanceFeedbackPhrase'))}")
        lines.append(
            "- **Monthly load (aerobic low / aerobic high / anaerobic)**: "
            f"{_num(balance.get('monthlyLoadAerobicLow'))} / "
            f"{_num(balance.get('monthlyLoadAerobicHigh'))} / "
            f"{_num(balance.get('monthlyLoadAnaerobic'))}"
        )
    vo2 = d.get("mostRecentVO2Max") or {}
    generic = vo2.get("generic") or {} if isinstance(vo2, dict) else {}
    gvo2 = generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue")
    if gvo2 is not None:
        lines.append(f"- **VO2 max**: {_num(gvo2, 1)} ml/kg/min")
    return "\n".join(lines)


def _md_hrv(d: dict) -> str:
    d = d or {}
    s = d.get("hrvSummary") or d
    baseline = s.get("baseline") or {}
    lines = ["# Heart Rate Variability (HRV)", ""]
    lines.append(f"- **Status**: {_clean(s.get('status'))}")
    lines.append(f"- **Last night avg**: {_num(s.get('lastNightAvg'))} ms")
    lines.append(f"- **7-day avg**: {_num(s.get('weeklyAvg'))} ms")
    lines.append(f"- **Last night 5-min high**: {_num(s.get('lastNight5MinHigh'))} ms")
    if baseline:
        lines.append(
            f"- **Balanced baseline range**: {_num(baseline.get('balancedLow'))}"
            f"–{_num(baseline.get('balancedUpper'))} ms"
        )
    readings = d.get("hrvReadings") or []
    if readings:
        lines.append(f"- **Overnight readings**: {len(readings)} "
                     "(use json format for the full series)")
    return "\n".join(lines)


def _md_max_metrics(d: dict) -> str:
    d = _first(d)
    generic = d.get("generic") or {}
    cycling = d.get("cycling") or {}
    accl = d.get("heatAltitudeAcclimation") or {}
    lines = ["# VO2 Max & Fitness Age", ""]
    run_vo2 = generic.get("vo2MaxPreciseValue") or generic.get("vo2MaxValue")
    lines.append(f"- **VO2 max (running)**: {_num(run_vo2, 1)} ml/kg/min")
    if generic.get("fitnessAge") is not None:
        lines.append(f"- **Fitness age**: {_num(generic.get('fitnessAge'))} years")
    cyc_vo2 = cycling.get("vo2MaxPreciseValue") or cycling.get("vo2MaxValue")
    if cyc_vo2 is not None:
        lines.append(f"- **VO2 max (cycling)**: {_num(cyc_vo2, 1)} ml/kg/min")
    if accl:
        lines.append(f"- **Heat acclimation**: {_num(accl.get('heatAcclimationPercentage'))} %")
        lines.append(f"- **Altitude acclimation**: {_num(accl.get('altitudeAcclimation'))} m")
    return "\n".join(lines)


def _md_weekly(a: dict) -> str:
    lines = [f"# Weekly summary — {a['start_date']} → {a['end_date']}", ""]
    lines.append(f"- **Days with data**: {a['days_with_data']}/{a['days_requested']}")
    lines.append(f"- **Total steps**: {_num(a['total_steps'])} "
                 f"(avg {_num(a['avg_steps_per_day'])}/day)")
    lines.append(f"- **Total distance**: {_num(a['total_distance_km'], 1)} km")
    lines.append(f"- **Total calories**: {_num(a['total_calories'])} kcal "
                 f"(active {_num(a['total_active_calories'])})")
    lines.append(f"- **Total floors**: {_num(a['total_floors'])}")
    lines.append(f"- **Avg resting HR**: {_num(a['avg_resting_hr'])} bpm")
    lines.append(f"- **Avg stress**: {_num(a['avg_stress'])}")
    lines.append(f"- **Intensity minutes**: {_num(a['total_intensity_minutes'])} "
                 f"(moderate {_num(a['moderate_intensity_minutes'])}, "
                 f"vigorous {_num(a['vigorous_intensity_minutes'])})")
    if a.get("best_day"):
        lines.append(f"- **Most active day**: {a['best_day']['date']} "
                     f"({_num(a['best_day']['steps'])} steps)")
    return "\n".join(lines)


def _aggregate_days(
    start_date: str, end_date: str, days_requested: int, summaries: list
) -> dict:
    """Aggregate a list of daily user-summary dicts into weekly totals/averages."""

    def vals(key: str) -> list:
        return [x.get(key) for x in summaries if x.get(key) is not None]

    steps = vals("totalSteps")
    total_steps = int(sum(steps))
    rhr = vals("restingHeartRate")
    stress = vals("averageStressLevel")
    mod = int(sum(vals("moderateIntensityMinutes")))
    vig = int(sum(vals("vigorousIntensityMinutes")))
    n = len(summaries)

    best = None
    if summaries:
        top = max(summaries, key=lambda x: x.get("totalSteps") or 0)
        if top.get("totalSteps"):
            best = {"date": top.get("calendarDate"), "steps": top.get("totalSteps")}

    return {
        "start_date": start_date,
        "end_date": end_date,
        "days_requested": days_requested,
        "days_with_data": n,
        "total_steps": total_steps,
        "avg_steps_per_day": round(total_steps / n) if n else 0,
        "total_distance_km": round(sum(vals("totalDistanceMeters")) / 1000.0, 2),
        "total_calories": int(sum(vals("totalKilocalories"))),
        "total_active_calories": int(sum(vals("activeKilocalories"))),
        "total_floors": int(sum(vals("floorsAscended"))),
        "avg_resting_hr": round(sum(rhr) / len(rhr)) if rhr else None,
        "avg_stress": round(sum(stress) / len(stress)) if stress else None,
        "total_intensity_minutes": mod + vig,
        "moderate_intensity_minutes": mod,
        "vigorous_intensity_minutes": vig,
        "best_day": best,
        "per_day": [
            {
                "date": x.get("calendarDate"),
                "steps": x.get("totalSteps"),
                "restingHeartRate": x.get("restingHeartRate"),
            }
            for x in summaries
        ],
    }


# ---------------------------------------------------------------------------
# Tools — Profile
# ---------------------------------------------------------------------------


@mcp.tool(name="garmin_get_profile", annotations={"title": "Get Garmin Profile", **_READ_ONLY})
async def garmin_get_profile(params: _Base) -> str:
    """Return basic account info: full name, username, and unit system.

    Useful as a first call to confirm authentication works and to learn
    whether the account reports in metric or statute (imperial) units.

    Args:
        params (_Base): Only ``response_format`` ('markdown' | 'json').

    Returns:
        str: Profile summary. JSON schema: {"fullName": str, "userName": str,
        "unitSystem": str}. On failure: "Error: <message>".
    """
    try:
        api = await asyncio.to_thread(client.get_api)
        full_name = await asyncio.to_thread(api.get_full_name)
        unit_system = await asyncio.to_thread(api.get_unit_system)
        data = {
            "fullName": full_name,
            "userName": getattr(api, "username", None) or getattr(api, "display_name", None),
            "unitSystem": unit_system,
        }
        return _format(data, params.response_format, _md_profile)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tools — Activities
# ---------------------------------------------------------------------------


@mcp.tool(name="garmin_list_activities", annotations={"title": "List Garmin Activities", **_READ_ONLY})
async def garmin_list_activities(params: ListActivitiesInput) -> str:
    """List recorded activities (runs, rides, swims, walks, workouts, ...).

    Two modes:
    - No dates: returns the most recent activities (paginated via ``start`` /
      ``limit``).
    - With ``start_date`` + ``end_date``: returns activities in that inclusive
      day range, optionally filtered by ``activity_type``.

    Args:
        params (ListActivitiesInput): limit, start, optional start_date /
            end_date / activity_type, and response_format.

    Returns:
        str: A list of activities. Each item includes activityId, activityName,
        activityType.typeKey, startTimeLocal, distance (m), duration (s),
        averageHR, maxHR, calories, elevationGain. Use ``activityId`` with
        garmin_get_activity for full detail. On failure: "Error: <message>".

    Examples:
        - "My last 5 runs" -> limit=5, activity_type not needed if recent
        - "All cycling activities in June 2024" -> start_date=2024-06-01,
          end_date=2024-06-30, activity_type='cycling'
    """
    try:
        if params.start_date and params.end_date:
            _check_range(params.start_date, params.end_date)
            items = await _call(
                lambda api: api.get_activities_by_date(
                    params.start_date, params.end_date, params.activity_type
                )
            )
            items = items[: params.limit]
        elif params.start_date or params.end_date:
            return (
                "Error: Provide both start_date and end_date together, "
                "or neither (to list most recent activities)."
            )
        else:
            items = await _call(
                lambda api: api.get_activities(params.start, params.limit)
            )
        return _format(items, params.response_format, _md_activities)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_activity", annotations={"title": "Get Garmin Activity Detail", **_READ_ONLY})
async def garmin_get_activity(params: ActivityInput) -> str:
    """Fetch detailed metrics for one activity by its ID.

    Returns the activity summary (distance, duration, speed, heart rate,
    calories, elevation, power) and optionally per-split laps and weather.
    Large GPS/sensor sample arrays are stripped to keep responses compact.

    Args:
        params (ActivityInput): activity_id (required), include_splits,
            include_weather, response_format.

    Returns:
        str: Activity detail. Markdown shows a readable summary; JSON returns
        the summaryDTO plus optional ``_splits`` and ``_weather`` keys.
        On failure: "Error: <message>".
    """
    try:
        details = await _call(
            lambda api: api.get_activity_details(params.activity_id, maxchart=0, maxpoly=0)
        )
        if isinstance(details, dict):
            # Drop the heavy per-second sample arrays regardless of maxchart.
            for heavy in ("activityDetailMetrics", "metricDescriptors", "geoPolylineDTO"):
                details.pop(heavy, None)

        if params.include_splits:
            try:
                splits = await _call(
                    lambda api: api.get_activity_splits(params.activity_id)
                )
                details["_splits"] = (splits or {}).get("lapDTOs", splits)
            except Exception:
                details["_splits"] = None

        if params.include_weather:
            try:
                details["_weather"] = await _call(
                    lambda api: api.get_activity_weather(params.activity_id)
                )
            except Exception:
                details["_weather"] = None

        return _format(details, params.response_format, _md_activity)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tools — Summaries & wellness
# ---------------------------------------------------------------------------


@mcp.tool(name="garmin_get_daily_summary", annotations={"title": "Get Daily Wellness Summary", **_READ_ONLY})
async def garmin_get_daily_summary(params: DateInput) -> str:
    """Get the all-in-one daily wellness summary for a single day.

    Combines the headline stats a user sees on the Garmin Connect dashboard:
    steps (+goal), distance, floors, total/active calories, resting & min/max
    heart rate, average stress, Body Battery range, intensity minutes, SpO2.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Daily summary. Key JSON fields: calendarDate, totalSteps,
        dailyStepGoal, totalDistanceMeters, floorsAscended, totalKilocalories,
        activeKilocalories, restingHeartRate, min/maxHeartRate,
        averageStressLevel, bodyBattery{Lowest,Highest,MostRecent}Value,
        moderate/vigorousIntensityMinutes, averageSpo2. On failure: "Error: ...".
    """
    try:
        data = await _call(lambda api: api.get_user_summary(params.cdate))
        return _format(data, params.response_format, _md_daily_summary)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_heart_rate", annotations={"title": "Get Daily Heart Rate", **_READ_ONLY})
async def garmin_get_heart_rate(params: DateInput) -> str:
    """Get heart-rate data for a single day.

    Includes resting HR, daily min/max, 7-day average resting HR, and (in JSON
    format) the intraday heart-rate time series (``heartRateValues``: arrays of
    [epoch_ms, bpm]).

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Heart-rate data. On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_heart_rates(params.cdate))
        return _format(data, params.response_format, _md_heart_rate)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_sleep", annotations={"title": "Get Sleep Data", **_READ_ONLY})
async def garmin_get_sleep(params: DateInput) -> str:
    """Get sleep data for a single night (keyed by the wake-up day).

    Includes total sleep time, sleep-stage breakdown (deep/light/REM/awake),
    the overall sleep score, overnight HRV, and resting heart rate.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Sleep summary. Key JSON path: dailySleepDTO.{sleepTimeSeconds,
        deepSleepSeconds, lightSleepSeconds, remSleepSeconds, awakeSleepSeconds,
        sleepScores.overall.value}. On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_sleep_data(params.cdate))
        return _format(data, params.response_format, _md_sleep)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_stress", annotations={"title": "Get Stress Data", **_READ_ONLY})
async def garmin_get_stress(params: DateInput) -> str:
    """Get stress data for a single day.

    Includes average and max stress level (0-100) and time spent in each
    stress band (rest / low / medium / high), given in seconds.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Stress summary. Key JSON fields: avgStressLevel, maxStressLevel,
        restStressDuration, lowStressDuration, mediumStressDuration,
        highStressDuration. On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_stress_data(params.cdate))
        return _format(data, params.response_format, _md_stress)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_body_battery", annotations={"title": "Get Body Battery", **_READ_ONLY})
async def garmin_get_body_battery(params: DateRangeInput) -> str:
    """Get Body Battery energy data over a date range (inclusive).

    Body Battery estimates the body's energy reserves (0-100). Each day
    reports how much was charged vs. drained and the intraday value series.

    Args:
        params (DateRangeInput): start_date, end_date (default today),
            response_format.

    Returns:
        str: Per-day Body Battery. Each entry: date, charged, drained,
        bodyBatteryValuesArray ([epoch_ms, level]). On failure: "Error: ...".
    """
    try:
        _check_range(params.start_date, params.end_date)
        data = await _call(
            lambda api: api.get_body_battery(params.start_date, params.end_date)
        )
        return _format(data, params.response_format, _md_body_battery)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_steps", annotations={"title": "Get Intraday Steps", **_READ_ONLY})
async def garmin_get_steps(params: DateInput) -> str:
    """Get intraday step data for a single day (15-minute buckets).

    Returns the per-interval step counts along with activity level for each
    bucket. For just the daily total, prefer garmin_get_daily_summary.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Intraday steps. JSON is a list of {startGMT, endGMT, steps,
        primaryActivityLevel}. On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_steps_data(params.cdate))
        return _format(data, params.response_format, _md_steps)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tools — Body composition
# ---------------------------------------------------------------------------


@mcp.tool(name="garmin_get_body_composition", annotations={"title": "Get Body Composition", **_READ_ONLY})
async def garmin_get_body_composition(params: DateRangeInput) -> str:
    """Get body composition measurements over a date range (inclusive).

    Sourced from a Garmin smart scale (e.g. Index). Reports weight, body-fat %,
    BMI, muscle mass, and body-water %, both as a range average and as
    individual measurements.

    Args:
        params (DateRangeInput): start_date, end_date (default today),
            response_format.

    Returns:
        str: Body composition. JSON: {totalAverage: {weight (g), bodyFat, bmi,
        muscleMass (g), bodyWater}, dateWeightList: [{date (epoch_ms), weight,
        bodyFat, bmi, ...}]}. Weight/muscle are grams. On failure: "Error: ...".
    """
    try:
        _check_range(params.start_date, params.end_date)
        data = await _call(
            lambda api: api.get_body_composition(params.start_date, params.end_date)
        )
        return _format(data, params.response_format, _md_body_composition)
    except Exception as e:
        return _handle_error(e)


# ---------------------------------------------------------------------------
# Tools — Training & performance
# ---------------------------------------------------------------------------


@mcp.tool(name="garmin_get_training_readiness", annotations={"title": "Get Training Readiness", **_READ_ONLY})
async def garmin_get_training_readiness(params: DateInput) -> str:
    """Get the Training Readiness score for a single day.

    Training Readiness (0-100) tells you how prepared your body is to train,
    combining sleep, recovery time, HRV, acute training load, and stress
    history. Higher is better. Only available on newer Garmin devices.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Readiness summary. Key JSON fields: score, level, feedbackShort,
        sleepScore, recoveryTime, hrvFactorFeedback, hrvWeeklyAverage,
        stressHistoryFactorFeedback, acuteLoad. On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_training_readiness(params.cdate))
        if not data:
            return (
                f"No training readiness data for {params.cdate}. This metric "
                "requires a compatible Garmin device that computes readiness."
            )
        return _format(data, params.response_format, _md_training_readiness)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_training_status", annotations={"title": "Get Training Status", **_READ_ONLY})
async def garmin_get_training_status(params: DateInput) -> str:
    """Get Training Status and training load for a single day.

    Training Status interprets your recent training (e.g. PRODUCTIVE,
    MAINTAINING, PEAKING, OVERREACHING, DETRAINING, RECOVERY) from your VO2 max
    trend and training load. Also reports the weekly training load, the optimal
    load range ("load tunnel"), the acute:chronic load ratio, and the monthly
    aerobic/anaerobic load balance. Requires a compatible Garmin device.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Training status summary. Key JSON paths: mostRecentTrainingStatus.
        latestTrainingStatusData.<deviceId>.{trainingStatusKey,
        trainingStatusFeedbackPhrase, weeklyTrainingLoad, loadTunnelMin,
        loadTunnelMax, acuteTrainingLoadDTO}, and mostRecentTrainingLoadBalance.
        metricsTrainingLoadBalanceDTOMap.<deviceId>.{monthlyLoadAerobicLow,
        monthlyLoadAerobicHigh, monthlyLoadAnaerobic, trainingBalanceFeedbackPhrase}.
        On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_training_status(params.cdate))
        if not data:
            return (
                f"No training status data for {params.cdate}. This metric "
                "requires a compatible Garmin device with recent training."
            )
        return _format(data, params.response_format, _md_training_status)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_hrv", annotations={"title": "Get HRV Status", **_READ_ONLY})
async def garmin_get_hrv(params: DateInput) -> str:
    """Get overnight Heart Rate Variability (HRV) status for a single day.

    HRV reflects recovery and autonomic balance. Reports last-night average,
    7-day average, the status (BALANCED / UNBALANCED / LOW / POOR), and the
    personalized balanced baseline range. Requires a device worn overnight.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: HRV summary. Key JSON path: hrvSummary.{status, lastNightAvg,
        weeklyAvg, lastNight5MinHigh, baseline.{balancedLow, balancedUpper}}.
        On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_hrv_data(params.cdate))
        if not data:
            return (
                f"No HRV data for {params.cdate}. HRV status requires a "
                "compatible Garmin device worn overnight."
            )
        return _format(data, params.response_format, _md_hrv)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_vo2max", annotations={"title": "Get VO2 Max & Fitness Age", **_READ_ONLY})
async def garmin_get_vo2max(params: DateInput) -> str:
    """Get VO2 max, fitness age, and acclimation for a single day.

    VO2 max estimates cardiorespiratory fitness (ml/kg/min) — separately for
    running and cycling. Also returns fitness age and heat/altitude
    acclimation when the device provides them.

    Args:
        params (DateInput): cdate (YYYY-MM-DD, default today), response_format.

    Returns:
        str: Fitness metrics. Key JSON path: generic.{vo2MaxValue,
        vo2MaxPreciseValue, fitnessAge}, cycling.{vo2MaxValue},
        heatAltitudeAcclimation.{heatAcclimationPercentage, altitudeAcclimation}.
        On failure: "Error: <message>".
    """
    try:
        data = await _call(lambda api: api.get_max_metrics(params.cdate))
        if not data:
            return f"No VO2 max / fitness metrics available for {params.cdate}."
        return _format(data, params.response_format, _md_max_metrics)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(name="garmin_get_weekly_summary", annotations={"title": "Get Weekly Wellness Summary", **_READ_ONLY})
async def garmin_get_weekly_summary(params: WeeklySummaryInput) -> str:
    """Aggregate daily wellness stats over a trailing window (default 7 days).

    Fetches each day's summary in the window ending on ``end_date`` and rolls
    them up into totals and averages: total/avg steps, distance, calories,
    floors, average resting HR, average stress, intensity minutes, and the
    most active day. Days without data are skipped.

    Args:
        params (WeeklySummaryInput): end_date (default today), days (1-31,
            default 7), response_format.

    Returns:
        str: Aggregated summary. JSON fields: start_date, end_date,
        days_with_data, total_steps, avg_steps_per_day, total_distance_km,
        total_calories, total_active_calories, total_floors, avg_resting_hr,
        avg_stress, total/moderate/vigorous_intensity_minutes, best_day,
        per_day[]. On failure: "Error: <message>".

    Examples:
        - "How did my week look?" -> defaults (last 7 days)
        - "Aggregate the last 30 days ending 2024-06-30" -> end_date=2024-06-30, days=30
    """
    try:
        end = datetime.strptime(params.end_date, _DATE_FMT).date()
        dates = [(end - timedelta(days=i)).strftime(_DATE_FMT) for i in range(params.days)]
        dates.reverse()  # chronological order (oldest first)

        api = await asyncio.to_thread(client.get_api)
        summaries = []
        for d in dates:
            try:
                # Sequential: garminconnect's session is not safe for concurrent use.
                s = await asyncio.to_thread(api.get_user_summary, d)
            except Exception:
                continue  # skip days the API can't return (e.g. future/no data)
            if s and s.get("totalSteps") is not None:
                summaries.append(s)

        agg = _aggregate_days(dates[0], params.end_date, params.days, summaries)
        return _format(agg, params.response_format, _md_weekly)
    except Exception as e:
        return _handle_error(e)


def main() -> None:
    """Console-script / module entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
