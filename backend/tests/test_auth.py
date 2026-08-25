"""Authentication and session behavior tests."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.models.session import Session as AuthSession
from app.models.user import UserStatus
from app.services.auth import create_session, create_user, hash_session_secret, revoke_session
from app.services.passwords import hash_password, verify_password


@pytest.fixture
def user(database):
    return create_user(database, " Pilot.User ", "Test Pilot", " Pilot@Example.com ", "a-valid-test-password")


def test_password_hashing_and_verification():
    password_hash = hash_password("a-valid-test-password")

    assert password_hash.startswith("$argon2id$")
    assert verify_password("a-valid-test-password", password_hash)
    assert not verify_password("wrong-test-password", password_hash)
    assert "a-valid-test-password" not in password_hash


def test_user_values_are_normalized(user):
    assert user.username == "pilot.user"
    assert user.email == "pilot@example.com"
    assert user.password_hash.startswith("$argon2id$")


def test_duplicate_username_and_email_are_rejected(database, user):
    with pytest.raises(ValueError):
        create_user(database, "PILOT.USER", "Another", "other@example.com", "another-valid-password")
    with pytest.raises(ValueError):
        create_user(database, "other-user", "Another", "PILOT@EXAMPLE.COM", "another-valid-password")


def test_session_creation_persistence_and_secret_is_hashed(database, user):
    session, raw_secret = create_session(database, user, "127.0.0.1", "test-agent")

    persisted = database.scalar(select(AuthSession).where(AuthSession.id == session.id))
    assert persisted is not None
    assert persisted.session_secret_hash == hash_session_secret(raw_secret)
    assert raw_secret not in persisted.session_secret_hash
    assert persisted.client_ip == "127.0.0.1"


def test_session_expiration_and_revocation(database, user):
    session, raw_secret = create_session(database, user, None, None)
    session.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    database.commit()

    from app.services.auth import resolve_session

    assert resolve_session(database, raw_secret) is None
    session.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)
    database.commit()
    revoke_session(database, session)
    assert resolve_session(database, raw_secret) is None


def test_successful_login_me_and_logout(client, user):
    login = client.post("/api/v1/auth/login", json={"identifier": "PILOT@EXAMPLE.COM", "password": "a-valid-test-password"})

    assert login.status_code == 200
    assert login.json()["user"]["username"] == "pilot.user"
    assert "password_hash" not in login.text
    assert "a-valid-test-password" not in login.text
    cookie = login.cookies.get("aeroguard_session")
    assert cookie
    assert login.headers["set-cookie"].lower().find("httponly") >= 0
    assert "samesite=lax" in login.headers["set-cookie"].lower()

    me = client.get("/api/v1/me")
    assert me.status_code == 200
    assert me.json()["email"] == "pilot@example.com"

    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    assert client.get("/api/v1/me").status_code == 401


def test_invalid_and_unknown_credentials_have_same_error(client, user):
    wrong_password = client.post("/api/v1/auth/login", json={"identifier": "pilot.user", "password": "wrong-test-password"})
    unknown_user = client.post("/api/v1/auth/login", json={"identifier": "unknown-user", "password": "wrong-test-password"})

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json()["error"]["code"] == unknown_user.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"
    assert wrong_password.json()["error"]["message"] == unknown_user.json()["error"]["message"]


def test_disabled_user_cannot_login_or_use_session(client, user, database):
    user.status = UserStatus.DISABLED
    database.commit()

    login = client.post("/api/v1/auth/login", json={"identifier": "pilot.user", "password": "a-valid-test-password"})
    assert login.status_code == 401
    assert login.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


def test_missing_and_invalid_session_are_unauthenticated(client):
    missing = client.get("/api/v1/me")
    client.cookies.set("aeroguard_session", "invalid-test-session")
    invalid = client.get("/api/v1/me")

    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["error"]["code"] == invalid.json()["error"]["code"] == "AUTH_UNAUTHENTICATED"
    assert missing.headers["X-Correlation-ID"]


def test_expired_and_revoked_sessions_have_stable_failures(client, user, database):
    session, expired_secret = create_session(database, user, None, None)
    session.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=1)
    database.commit()
    client.cookies.set("aeroguard_session", expired_secret)
    assert client.get("/api/v1/me").json()["error"]["code"] == "AUTH_SESSION_EXPIRED"

    session.expires_at = datetime.now(UTC).replace(tzinfo=None) + timedelta(minutes=5)
    revoke_session(database, session)
    client.cookies.set("aeroguard_session", expired_secret)
    assert client.get("/api/v1/me").json()["error"]["code"] == "AUTH_SESSION_REVOKED"


def test_disallowed_origin_is_rejected(client):
    response = client.post("/api/v1/auth/logout", headers={"Origin": "https://not-allowed.example"})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_origin_rejected"


def test_login_replaces_preexisting_cookie(client, user):
    client.cookies.set("aeroguard_session", "unauthenticated-old-session")
    login = client.post("/api/v1/auth/login", json={"identifier": "pilot.user", "password": "a-valid-test-password"})

    assert login.status_code == 200
    assert login.cookies.get("aeroguard_session") != "unauthenticated-old-session"