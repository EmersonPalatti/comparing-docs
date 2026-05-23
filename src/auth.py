from __future__ import annotations

import hmac
import os
from collections.abc import Mapping, MutableMapping
from datetime import UTC, datetime, timedelta
from typing import Any


USERNAME_ENV = "APP_USERNAME"
PASSWORD_ENV = "APP_PASSWORD"
FAILED_ATTEMPTS_KEY = "failed_attempts"
FIRST_FAILED_AT_KEY = "first_failed_at"
LOCKED_UNTIL_KEY = "locked_until"


def get_expected_credentials(
    secrets: Mapping[str, Any] | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[str | None, str | None]:
    environ = environ or os.environ
    username = environ.get(USERNAME_ENV) or secret_value(secrets, "username")
    password = environ.get(PASSWORD_ENV) or secret_value(secrets, "password")
    return username, password


def secret_value(secrets: Mapping[str, Any] | None, key: str) -> str | None:
    if not secrets:
        return None

    auth_section = mapping_get(secrets, "auth")
    if isinstance(auth_section, Mapping):
        value = mapping_get(auth_section, key)
        if value:
            return str(value)

    upper_value = mapping_get(secrets, key.upper())
    if upper_value:
        return str(upper_value)
    return None


def mapping_get(mapping: Mapping[str, Any], key: str) -> Any:
    try:
        return mapping.get(key)
    except Exception:
        return None


def credentials_configured(username: str | None, password: str | None) -> bool:
    return bool(username and password)


def credentials_match(
    provided_username: str,
    provided_password: str,
    expected_username: str | None,
    expected_password: str | None,
) -> bool:
    if not credentials_configured(expected_username, expected_password):
        return False
    return hmac.compare_digest(provided_username, expected_username or "") and hmac.compare_digest(
        provided_password,
        expected_password or "",
    )


def _utcnow() -> datetime:
    return datetime.now(UTC)


def initialize_login_state(session_state: MutableMapping[str, Any]) -> None:
    session_state.setdefault(FAILED_ATTEMPTS_KEY, 0)
    session_state.setdefault(FIRST_FAILED_AT_KEY, None)
    session_state.setdefault(LOCKED_UNTIL_KEY, None)


def is_login_locked(session_state: MutableMapping[str, Any], now: datetime | None = None) -> tuple[bool, timedelta]:
    locked_until = session_state.get(LOCKED_UNTIL_KEY)
    if not isinstance(locked_until, datetime):
        return False, timedelta(0)
    now = now or _utcnow()
    if locked_until <= now:
        session_state[LOCKED_UNTIL_KEY] = None
        return False, timedelta(0)
    return True, locked_until - now


def register_failed_attempt(
    session_state: MutableMapping[str, Any],
    *,
    now: datetime | None = None,
    max_attempts: int = 5,
    lock_duration: timedelta = timedelta(minutes=15),
) -> bool:
    now = now or _utcnow()
    attempts = int(session_state.get(FAILED_ATTEMPTS_KEY, 0)) + 1
    session_state[FAILED_ATTEMPTS_KEY] = attempts
    if session_state.get(FIRST_FAILED_AT_KEY) is None:
        session_state[FIRST_FAILED_AT_KEY] = now
    if attempts >= max_attempts:
        session_state[LOCKED_UNTIL_KEY] = now + lock_duration
        session_state[FAILED_ATTEMPTS_KEY] = 0
        session_state[FIRST_FAILED_AT_KEY] = None
        return True
    return False


def clear_login_failures(session_state: MutableMapping[str, Any]) -> None:
    session_state[FAILED_ATTEMPTS_KEY] = 0
    session_state[FIRST_FAILED_AT_KEY] = None
    session_state[LOCKED_UNTIL_KEY] = None
