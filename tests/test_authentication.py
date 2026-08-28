from argon2 import PasswordHasher
from fastapi.testclient import TestClient

from app.authentication import (
    DUMMY_PASSWORD_HASH,
    hash_password,
    hash_session_token,
    password_needs_rehash,
    verify_password,
)
from app.data import ACCOUNTS, SESSIONS
from app.main import SESSION_LIFETIME, app
from app.models import UserAccount


TEST_PASSWORD = "ExpenseGuard Test Password 2026"
DEMO_EMAIL = "noman@example.com"
DEMO_PASSWORD = "Noman Demo Password 2026"
GENERIC_LOGIN_ERROR = {"detail": "Invalid email or password."}

client = TestClient(app)


def test_hash_password_does_not_return_plaintext():
    password_hash = hash_password(TEST_PASSWORD)
    assert password_hash != TEST_PASSWORD


def test_password_hash_uses_argon2id():
    password_hash = hash_password(TEST_PASSWORD)
    assert password_hash.startswith("$argon2id$")


def test_correct_password_verifies():
    password_hash = hash_password(TEST_PASSWORD)
    assert verify_password(password_hash, TEST_PASSWORD) is True


def test_wrong_password_is_rejected():
    password_hash = hash_password(TEST_PASSWORD)
    assert verify_password(password_hash, "Another Test Password 2026") is False


def test_same_password_produces_different_hashes():
    first_hash = hash_password(TEST_PASSWORD)
    second_hash = hash_password(TEST_PASSWORD)

    assert first_hash != second_hash
    assert verify_password(first_hash, TEST_PASSWORD) is True
    assert verify_password(second_hash, TEST_PASSWORD) is True


def test_outdated_parameters_are_detected_for_rehash():
    legacy_hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    legacy_hash = legacy_hasher.hash(TEST_PASSWORD)

    assert password_needs_rehash(legacy_hash) is True


def test_successful_login_returns_fresh_bearer_token_and_normalizes_email():
    SESSIONS.clear()

    response = client.post(
        "/auth/login",
        json={"email": "  NOMAN@EXAMPLE.COM  ", "password": DEMO_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str)
    assert body["access_token"]


def test_wrong_password_and_unknown_account_have_same_public_error():
    wrong_password = client.post(
        "/auth/login",
        json={"email": DEMO_EMAIL, "password": "Wrong Demo Password 2026"},
    )
    unknown_account = client.post(
        "/auth/login",
        json={
            "email": "does-not-exist@example.com",
            "password": "Wrong Demo Password 2026",
        },
    )

    assert wrong_password.status_code == 401
    assert unknown_account.status_code == 401
    assert wrong_password.json() == GENERIC_LOGIN_ERROR
    assert unknown_account.json() == GENERIC_LOGIN_ERROR


def test_unknown_account_uses_dummy_argon2_verification(monkeypatch):
    observed_hashes: list[str] = []

    def fake_verify(password_hash: str, password: str) -> bool:
        observed_hashes.append(password_hash)
        return False

    monkeypatch.setattr("app.main.verify_password", fake_verify)

    response = client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": TEST_PASSWORD},
    )

    assert response.status_code == 401
    assert observed_hashes == [DUMMY_PASSWORD_HASH]


def test_disabled_account_is_rejected_with_generic_error():
    email = "disabled@example.com"
    ACCOUNTS[email] = UserAccount(
        user_id=1,
        email=email,
        password_hash=hash_password(TEST_PASSWORD),
        is_active=False,
    )

    try:
        response = client.post(
            "/auth/login",
            json={"email": email, "password": TEST_PASSWORD},
        )

        assert response.status_code == 401
        assert response.json() == GENERIC_LOGIN_ERROR
    finally:
        ACCOUNTS.pop(email, None)


def test_raw_bearer_token_is_not_stored_server_side():
    SESSIONS.clear()

    response = client.post(
        "/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )

    assert response.status_code == 200
    raw_token = response.json()["access_token"]
    token_hash = hash_session_token(raw_token)

    assert raw_token not in SESSIONS
    assert token_hash in SESSIONS
    session = SESSIONS[token_hash]
    assert session.token_hash == token_hash
    assert raw_token not in repr(session)


def test_two_successful_logins_receive_different_tokens():
    SESSIONS.clear()

    first = client.post(
        "/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    second = client.post(
        "/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["access_token"] != second.json()["access_token"]
    assert len(SESSIONS) == 2


def test_new_session_has_explicit_absolute_expiration():
    SESSIONS.clear()

    response = client.post(
        "/auth/login",
        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )

    assert response.status_code == 200
    token_hash = hash_session_token(response.json()["access_token"])
    session = SESSIONS[token_hash]

    assert session.expires_at > session.created_at
    assert session.expires_at - session.created_at == SESSION_LIFETIME
    assert session.revoked_at is None


def test_successful_login_upgrades_outdated_password_hash():
    email = "legacy@example.com"
    legacy_hasher = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1)
    legacy_hash = legacy_hasher.hash(TEST_PASSWORD)
    account = UserAccount(
        user_id=1,
        email=email,
        password_hash=legacy_hash,
    )
    ACCOUNTS[email] = account

    try:
        response = client.post(
            "/auth/login",
            json={"email": email, "password": TEST_PASSWORD},
        )

        assert response.status_code == 200
        assert account.password_hash != legacy_hash
        assert verify_password(account.password_hash, TEST_PASSWORD) is True
        assert password_needs_rehash(account.password_hash) is False
    finally:
        ACCOUNTS.pop(email, None)
