"""Smoke tests for auth flow."""
import pytest

from backend.models.user import User
from backend.services.auth_service import hash_password


@pytest.fixture
async def admin_user(session):
    u = User(
        username="testadmin",
        password_hash=hash_password("secret123"),
        full_name="Test Admin",
        role="admin",
        is_active=True,
    )
    session.add(u)
    await session.commit()
    return u


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "secret123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]
    assert body["user"]["username"] == "testadmin"


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "wrong"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_requires_token(client):
    r = await client.get("/api/v1/auth/me")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_me_with_token(client, admin_user):
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "testadmin", "password": "secret123"},
    )
    token = login.json()["tokens"]["access_token"]
    r = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["username"] == "testadmin"
