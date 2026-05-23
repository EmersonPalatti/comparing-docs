from __future__ import annotations

import hmac
import logging
import os
import time
from collections.abc import Mapping
from typing import Any

from src.config import (
    AUTH_BASE_DELAY_SECONDS,
    AUTH_LOCKOUT_SECONDS,
    AUTH_MAX_ATTEMPTS,
    AUTH_MAX_DELAY_SECONDS,
    AUTH_REGISTRY_MAX_ENTRIES,
    AUTH_RATE_WINDOW_SECONDS,
    AUTH_TRUST_PROXY_HEADERS,
)


USERNAME_ENV = "APP_USERNAME"
PASSWORD_ENV = "APP_PASSWORD"
AUTH_REGISTRY: dict[str, dict[str, float | int]] = {}
WEAK_USERNAMES = {"admin", "root", "user", "test"}
WEAK_PASSWORDS = {
    "admin",
    "123456",
    "password",
    "senha",
    "changeme",
    "configure-a-senha-no-streamlit-cloud",
}
LOGGER = logging.getLogger(__name__)


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


def credential_policy_ok(username: str | None, password: str | None) -> bool:
    if not username or not password:
        return False
    normalized_username = username.strip().lower()
    normalized_password = password.strip().lower()
    if len(password.strip()) < 12:
        return False
    if normalized_username in WEAK_USERNAMES:
        return False
    if normalized_password in WEAK_PASSWORDS:
        return False
    return True


def build_client_key(
    headers: Mapping[str, Any] | None = None,
    session_identifier: str | None = None,
    trust_proxy_headers: bool = AUTH_TRUST_PROXY_HEADERS,
) -> str:
    ip: str | None = None
    if headers and trust_proxy_headers:
        forwarded_for = str(mapping_get(headers, "x-forwarded-for") or "").split(",")[0].strip()
        real_ip = str(mapping_get(headers, "x-real-ip") or "").strip()
        ip = forwarded_for or real_ip or None
    if ip:
        return f"ip:{ip}"
    if session_identifier:
        return f"session:{session_identifier}"
    return "session:unknown"


def login_delay_seconds(client_key: str, now: float | None = None) -> float:
    state = _current_state(client_key, now=now)
    failures = int(state.get("failures", 0))
    if failures <= 1:
        return 0.0
    delay = AUTH_BASE_DELAY_SECONDS * (2 ** (failures - 2))
    return min(delay, AUTH_MAX_DELAY_SECONDS)


def is_locked_out(client_key: str, now: float | None = None) -> tuple[bool, int]:
    current_time = now if now is not None else time.time()
    state = _current_state(client_key, now=current_time)
    lock_until = float(state.get("lock_until", 0))
    if lock_until > current_time:
        return True, int(lock_until - current_time)
    return False, 0


def register_failed_attempt(client_key: str, now: float | None = None) -> tuple[bool, int]:
    current_time = now if now is not None else time.time()
    _prune_registry(now=current_time)
    state = _current_state(client_key, now=current_time)
    failures = int(state.get("failures", 0)) + 1
    state["failures"] = failures
    state["last_failure"] = current_time
    lock_until = 0.0
    if failures >= AUTH_MAX_ATTEMPTS:
        lock_until = current_time + AUTH_LOCKOUT_SECONDS
        state["lock_until"] = lock_until
    AUTH_REGISTRY[client_key] = state
    LOGGER.warning("login_failed client=%s failures=%s lock_until=%s", client_key, failures, int(lock_until))
    return lock_until > current_time, int(max(lock_until - current_time, 0))


def register_successful_login(client_key: str) -> None:
    AUTH_REGISTRY.pop(client_key, None)
    LOGGER.info("login_success client=%s", client_key)


def _current_state(client_key: str, now: float | None = None) -> dict[str, float | int]:
    current_time = now if now is not None else time.time()
    _prune_registry(now=current_time)
    state = AUTH_REGISTRY.get(client_key, {}).copy()
    last_failure = float(state.get("last_failure", 0))
    if last_failure and current_time - last_failure > AUTH_RATE_WINDOW_SECONDS:
        state = {}
    state.setdefault("failures", 0)
    state.setdefault("lock_until", 0.0)
    return state


def _prune_registry(now: float | None = None) -> None:
    current_time = now if now is not None else time.time()
    stale_keys = [
        key
        for key, state in AUTH_REGISTRY.items()
        if current_time - float(state.get("last_failure", 0)) > AUTH_RATE_WINDOW_SECONDS
    ]
    for key in stale_keys:
        AUTH_REGISTRY.pop(key, None)

    overflow = len(AUTH_REGISTRY) - AUTH_REGISTRY_MAX_ENTRIES
    if overflow <= 0:
        return

    oldest_keys = sorted(
        AUTH_REGISTRY,
        key=lambda key: float(AUTH_REGISTRY[key].get("last_failure", 0)),
    )[:overflow]
    for key in oldest_keys:
        AUTH_REGISTRY.pop(key, None)
