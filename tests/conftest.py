"""Shared pytest fixtures for the Garmin MCP server tests.

All tests run against a ``FakeGarmin`` stand-in for ``garminconnect.Garmin``,
so no network access or real credentials are required. The fixtures patch the
module-level client singleton the tools use.
"""

from __future__ import annotations

import pytest

from garmin_mcp import server as srv


class FakeGarmin:
    """In-memory stand-in for ``garminconnect.Garmin``.

    Returns realistic, deterministic sample data shaped like the real Garmin
    Connect responses (including the list-wrapped and per-device-keyed quirks).
    """

    username = "test.user"

    # --- profile -----------------------------------------------------------
    def get_full_name(self) -> str:
        return "Test User"

    def get_unit_system(self) -> str:
        return "metric"

    # --- activities --------------------------------------------------------
    def get_activities(self, start: int, limit: int) -> list:
        items = [
            {
                "activityId": 1000 + i,
                "activityName": f"Activity {i}",
                "activityType": {"typeKey": "running" if i % 2 else "cycling"},
                "startTimeLocal": f"2026-07-{10 + i:02d} 06:30:00",
                "distance": 10000.0 + i * 100,
                "duration": 3000.0 + i * 60,
                "averageHR": 150 + i,
                "maxHR": 178,
                "calories": 700 + i * 10,
                "elevationGain": 80.0,
            }
            for i in range(5)
        ]
        return items[start : start + limit]

    def get_activities_by_date(self, start: str, end: str, atype) -> list:
        acts = self.get_activities(0, 10)
        if atype:
            acts = [a for a in acts if a["activityType"]["typeKey"] == atype]
        return acts

    def get_activity_details(self, activity_id, maxchart=0, maxpoly=0) -> dict:
        return {
            "activityDetailMetrics": [0] * 5000,  # heavy array to be stripped
            "metricDescriptors": [{"key": "x"}],
            "geoPolylineDTO": {"polyline": [1, 2, 3]},
            "summaryDTO": {
                "distance": 10250.5,
                "duration": 3210.0,
                "movingDuration": 3100.0,
                "averageSpeed": 3.19,
                "averageHR": 152,
                "maxHR": 178,
                "calories": 720,
                "elevationGain": 85.0,
                "averagePower": 240,
            },
        }

    def get_activity_splits(self, activity_id) -> dict:
        return {"lapDTOs": [{"distance": 1000, "duration": 300, "averageHR": 150}]}

    def get_activity_weather(self, activity_id) -> dict:
        return {"temp": 18, "weatherTypeDTO": {"desc": "Partly cloudy"}}

    # --- summaries & wellness ---------------------------------------------
    def get_user_summary(self, cdate: str) -> dict:
        # Steps vary by day-of-month so aggregation/best-day is deterministic.
        day = int(cdate.split("-")[-1])
        return {
            "calendarDate": cdate,
            "totalSteps": 1000 * day,
            "dailyStepGoal": 10000,
            "totalDistanceMeters": 700 * day,
            "floorsAscended": day,
            "totalKilocalories": 2000 + day,
            "activeKilocalories": 500 + day,
            "restingHeartRate": 50,
            "minHeartRate": 44,
            "maxHeartRate": 170,
            "averageStressLevel": 30,
            "bodyBatteryMostRecentValue": 60,
            "bodyBatteryLowestValue": 15,
            "bodyBatteryHighestValue": 90,
            "moderateIntensityMinutes": 20,
            "vigorousIntensityMinutes": 10,
            "averageSpo2": 96,
        }

    def get_heart_rates(self, cdate: str) -> dict:
        return {
            "calendarDate": cdate,
            "restingHeartRate": 48,
            "minHeartRate": 44,
            "maxHeartRate": 178,
            "lastSevenDaysAvgRestingHeartRate": 50,
            "heartRateValues": [[1, 60], [2, 62]],
        }

    def get_sleep_data(self, cdate: str) -> dict:
        return {
            "dailySleepDTO": {
                "calendarDate": cdate,
                "sleepTimeSeconds": 26400,
                "deepSleepSeconds": 5400,
                "lightSleepSeconds": 15000,
                "remSleepSeconds": 5000,
                "awakeSleepSeconds": 1000,
                "sleepScores": {"overall": {"value": 82}},
            },
            "avgOvernightHrv": 55,
            "restingHeartRate": 47,
        }

    def get_stress_data(self, cdate: str) -> dict:
        return {
            "calendarDate": cdate,
            "avgStressLevel": 32,
            "maxStressLevel": 88,
            "restStressDuration": 18000,
            "lowStressDuration": 12000,
            "mediumStressDuration": 6000,
            "highStressDuration": 1200,
        }

    def get_body_battery(self, start: str, end: str) -> list:
        return [
            {
                "date": start,
                "charged": 70,
                "drained": 55,
                "bodyBatteryValuesArray": [[1, 20], [2, 80], [3, 45]],
            }
        ]

    def get_steps_data(self, cdate: str) -> list:
        return [
            {"startGMT": "08:00", "endGMT": "08:15", "steps": 300, "primaryActivityLevel": "active"},
            {"startGMT": "08:15", "endGMT": "08:30", "steps": 1200, "primaryActivityLevel": "active"},
        ]

    def get_body_composition(self, start: str, end: str) -> dict:
        return {
            "totalAverage": {
                "weight": 72500,
                "bodyFat": 17.5,
                "bmi": 22.4,
                "muscleMass": 34000,
                "bodyWater": 58.2,
            },
            "dateWeightList": [
                {"date": 1753843200000, "weight": 72500, "bodyFat": 17.5, "bmi": 22.4}
            ],
        }

    # --- training & performance -------------------------------------------
    def get_training_readiness(self, cdate: str) -> list:
        return [
            {
                "score": 78,
                "level": "HIGH",
                "feedbackShort": "READY_TO_TRAIN",
                "feedbackLong": "GOOD_RECOVERY",
                "sleepScore": 82,
                "sleepScoreFactorFeedback": "GOOD",
                "recoveryTime": 360,
                "hrvFactorFeedback": "BALANCED",
                "hrvWeeklyAverage": 58,
                "stressHistoryFactorFeedback": "LOW",
                "acuteLoad": 245,
            }
        ]

    def get_training_status(self, cdate: str) -> dict:
        return {
            "mostRecentTrainingStatus": {
                "latestTrainingStatusData": {
                    "3113221234": {
                        "trainingStatusKey": "PRODUCTIVE",
                        "trainingStatusFeedbackPhrase": "PRODUCTIVE_1",
                        "weeklyTrainingLoad": 320,
                        "loadTunnelMin": 250,
                        "loadTunnelMax": 450,
                        "acuteTrainingLoadDTO": {"dailyAcuteChronicWorkloadRatio": 1.15},
                    }
                }
            },
            "mostRecentTrainingLoadBalance": {
                "metricsTrainingLoadBalanceDTOMap": {
                    "3113221234": {
                        "monthlyLoadAerobicLow": 180,
                        "monthlyLoadAerobicHigh": 90,
                        "monthlyLoadAnaerobic": 50,
                        "trainingBalanceFeedbackPhrase": "BALANCED",
                    }
                }
            },
            "mostRecentVO2Max": {"generic": {"vo2MaxValue": 52, "vo2MaxPreciseValue": 52.4}},
        }

    def get_hrv_data(self, cdate: str) -> dict:
        return {
            "hrvSummary": {
                "status": "BALANCED",
                "lastNightAvg": 55,
                "weeklyAvg": 58,
                "lastNight5MinHigh": 92,
                "baseline": {"balancedLow": 45, "balancedUpper": 70},
            },
            "hrvReadings": [{"t": 1, "v": 50}, {"t": 2, "v": 55}],
        }

    def get_max_metrics(self, cdate: str) -> list:
        return [
            {
                "generic": {"vo2MaxValue": 52, "vo2MaxPreciseValue": 52.4, "fitnessAge": 31},
                "cycling": {"vo2MaxValue": 48, "vo2MaxPreciseValue": 48.1},
                "heatAltitudeAcclimation": {
                    "heatAcclimationPercentage": 20,
                    "altitudeAcclimation": 300,
                },
            }
        ]


@pytest.fixture
def fake_api() -> FakeGarmin:
    """Return a fresh FakeGarmin instance."""
    return FakeGarmin()


@pytest.fixture
def patched(monkeypatch, fake_api):
    """Patch the tools' client singleton to return the fake API.

    Yields the FakeGarmin so tests can tweak or swap methods on it.
    """
    monkeypatch.setattr(srv.client, "get_api", lambda: fake_api)
    return fake_api
