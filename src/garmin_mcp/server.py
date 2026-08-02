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


def main() -> None:
    """Console-script / module entry point. Runs the server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
