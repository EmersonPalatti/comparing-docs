from src.auth import (
    AUTH_REGISTRY,
    build_client_key,
    credential_policy_ok,
    credentials_configured,
    credentials_match,
    get_expected_credentials,
    is_locked_out,
    login_delay_seconds,
    register_failed_attempt,
    register_successful_login,
)


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
    assert credentials_configured("analista", "segredo-super-forte") is True
    assert credentials_match("analista", "segredo-super-forte", "analista", "segredo-super-forte") is True
    assert credentials_match("analista", "wrong", "analista", "segredo-super-forte") is False
    assert credentials_match("admin", "secret", None, None) is False


def test_credential_policy_rejects_weak_values():
    assert credential_policy_ok("admin", "password") is False
    assert credential_policy_ok("user", "123456789012") is False
    assert credential_policy_ok("secure-user", "short") is False
    assert credential_policy_ok("secure-user", "senha-super-segura-2026") is True


def test_build_client_key_prefers_ip_and_falls_back_to_session():
    assert build_client_key(headers={"x-real-ip": "10.1.2.3"}, session_identifier="abc") == "ip:10.1.2.3"
    assert build_client_key(headers={}, session_identifier="abc") == "session:abc"


def test_bruteforce_controls_lock_and_reset_on_success():
    AUTH_REGISTRY.clear()
    client_key = "session:test"

    assert is_locked_out(client_key, now=1000.0) == (False, 0)
    assert login_delay_seconds(client_key, now=1000.0) == 0.0

    for _ in range(4):
        locked, _ = register_failed_attempt(client_key, now=1000.0)
        assert locked is False
    assert login_delay_seconds(client_key, now=1001.0) > 0

    locked, remaining = register_failed_attempt(client_key, now=1001.0)
    assert locked is True
    assert remaining > 0
    assert is_locked_out(client_key, now=1002.0)[0] is True

    register_successful_login(client_key)
    assert is_locked_out(client_key, now=1002.0) == (False, 0)
