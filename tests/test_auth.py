from src.auth import credentials_configured, credentials_match, get_expected_credentials


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
