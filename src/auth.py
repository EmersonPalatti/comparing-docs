from __future__ import annotations

import hmac
import os
from collections.abc import Mapping
from typing import Any


USERNAME_ENV = "APP_USERNAME"
PASSWORD_ENV = "APP_PASSWORD"


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
