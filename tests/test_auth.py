from datetime import UTC, datetime, timedelta

from src.auth import credentials_configured, credentials_match, get_expected_credentials
from src.auth import clear_login_failures, initialize_login_state, is_login_locked, register_failed_attempt


def test_get_expected_credentials_from_auth_secrets():
    username, password = get_expected_credentials(
        secrets={"auth": {"username": "admin", "password": "secret"}},
        environ={},
    )

    assert username == "admin"
    assert password == "secret"


def test_environment_credentials_take_precedence():
    username, password = get_expected_credentials(
        secrets={"auth": {"username": "admin", "password": "secret"}},
        environ={"APP_USERNAME": "local", "APP_PASSWORD": "local-secret"},
    )

    assert username == "local"
    assert password == "local-secret"


def test_credentials_match_uses_expected_values():
    assert credentials_configured("admin", "secret") is True
    assert credentials_match("admin", "secret", "admin", "secret") is True
    assert credentials_match("admin", "wrong", "admin", "secret") is False
    assert credentials_match("admin", "secret", None, None) is False


def test_failed_attempts_trigger_lock():
    state = {}
    now = datetime(2026, 5, 23, 10, 0, tzinfo=UTC)
    initialize_login_state(state)

    for _ in range(4):
        assert register_failed_attempt(state, now=now, max_attempts=5) is False
    assert state["failed_attempts"] == 4
    assert state["locked_until"] is None

    assert register_failed_attempt(state, now=now, max_attempts=5) is True
    assert state["failed_attempts"] == 0
    assert state["first_failed_at"] is None
    assert state["locked_until"] == now + timedelta(minutes=15)


def test_active_lock_is_reported():
    now = datetime(2026, 5, 23, 10, 0, tzinfo=UTC)
    state = {"locked_until": now + timedelta(minutes=3)}

    locked, remaining = is_login_locked(state, now=now)
    assert locked is True
    assert remaining == timedelta(minutes=3)


def test_lock_expires_and_is_cleared():
    now = datetime(2026, 5, 23, 10, 0, tzinfo=UTC)
    state = {"locked_until": now - timedelta(seconds=1)}

    locked, remaining = is_login_locked(state, now=now)
    assert locked is False
    assert remaining == timedelta(0)
    assert state["locked_until"] is None


def test_success_resets_failure_counters():
    now = datetime(2026, 5, 23, 10, 0, tzinfo=UTC)
    state = {}
    initialize_login_state(state)
    register_failed_attempt(state, now=now)
    register_failed_attempt(state, now=now)
    state["locked_until"] = now + timedelta(minutes=1)

    clear_login_failures(state)
    assert state["failed_attempts"] == 0
    assert state["first_failed_at"] is None
    assert state["locked_until"] is None
