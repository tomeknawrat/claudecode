"""Garmin Connect client wrapper.

Handles authentication against Garmin Connect using the (unofficial)
``garminconnect`` library, which is built on top of ``garth`` for the
OAuth token handshake. Tokens are cached on disk so that a login only has
to happen once (or when the cached tokens expire), which also lets the
server survive restarts without re-authenticating every time.

Credentials are read from the environment:

- ``GARMIN_EMAIL``       -- Garmin Connect account e-mail (required)
- ``GARMIN_PASSWORD``    -- Garmin Connect account password (required)
- ``GARMIN_TOKEN_STORE`` -- directory used to cache OAuth tokens
                            (optional, default: ``~/.garminconnect``)
- ``GARMIN_MFA_CODE``    -- one-time MFA/2FA code, only needed on first
                            login for accounts with two-factor auth enabled
- ``GARMIN_IS_CN``       -- set to ``1``/``true`` for accounts registered on
                            the Chinese ``garmin.cn`` domain (optional)
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Optional

try:
    from garminconnect import (
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )
except ImportError as exc:  # pragma: no cover - surfaced at runtime
    raise ImportError(
        "The 'garminconnect' package is required. Install it with "
        "'pip install garminconnect' (see requirements.txt)."
    ) from exc


class GarminAuthError(RuntimeError):
    """Raised when the server cannot authenticate against Garmin Connect."""


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _default_token_store() -> str:
    return os.environ.get(
        "GARMIN_TOKEN_STORE", str(Path.home() / ".garminconnect")
    )


class GarminClient:
    """Lazy, thread-safe singleton wrapper around ``garminconnect.Garmin``.

    The underlying ``Garmin`` object is created on first use and reused for
    subsequent calls. Because ``garminconnect`` is synchronous, tools run
    the blocking calls in a worker thread (via ``asyncio.to_thread``); a
    lock guards login so concurrent tool calls don't race on the handshake.
    """

    def __init__(self) -> None:
        self._api: Optional[Garmin] = None
        self._lock = threading.Lock()

    def _login(self) -> Garmin:
        email = os.environ.get("GARMIN_EMAIL", "").strip()
        password = os.environ.get("GARMIN_PASSWORD", "").strip()
        token_store = _default_token_store()

        api = Garmin(
            email=email or None,
            password=password or None,
            is_cn=_env_flag("GARMIN_IS_CN"),
            return_on_mfa=True,
        )

        # 1) Try cached tokens first — no credentials needed if still valid.
        try:
            api.login(token_store)
            return api
        except (FileNotFoundError, GarminConnectAuthenticationError, Exception):
            # Fall through to a fresh credential login below.
            pass

        if not email or not password:
            raise GarminAuthError(
                "No valid cached Garmin session and no credentials provided. "
                "Set GARMIN_EMAIL and GARMIN_PASSWORD environment variables "
                "(and GARMIN_MFA_CODE if two-factor auth is enabled)."
            )

        # 2) Fresh login with credentials. ``return_on_mfa=True`` makes the
        #    first call return a ("needs_mfa", state) tuple instead of
        #    prompting interactively, so we can feed a code from the env.
        result = api.login()
        if isinstance(result, tuple) and result[0] == "needs_mfa":
            mfa_code = os.environ.get("GARMIN_MFA_CODE", "").strip()
            if not mfa_code:
                raise GarminAuthError(
                    "Garmin account requires a two-factor (MFA) code. "
                    "Set GARMIN_MFA_CODE to the current code and retry. "
                    "Once logged in, tokens are cached and MFA is not needed "
                    "again until they expire."
                )
            api.resume_login(result[1], mfa_code)

        # Persist tokens so future runs skip the credential login entirely.
        try:
            api.garth.dump(token_store)
        except Exception:
            # Token caching is best-effort; a failure here is non-fatal.
            pass

        return api

    def get_api(self) -> Garmin:
        """Return an authenticated ``Garmin`` client, logging in if needed."""
        if self._api is not None:
            return self._api
        with self._lock:
            if self._api is None:
                try:
                    self._api = self._login()
                except (
                    GarminConnectAuthenticationError,
                    GarminConnectConnectionError,
                    GarminConnectTooManyRequestsError,
                ) as exc:
                    raise GarminAuthError(str(exc)) from exc
        return self._api

    def reset(self) -> None:
        """Drop the cached session so the next call re-authenticates."""
        with self._lock:
            self._api = None


# Module-level singleton used by all tools.
client = GarminClient()
