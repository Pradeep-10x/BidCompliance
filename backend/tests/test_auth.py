import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_register_user_success(client: AsyncClient):
    payload = {
        "email": "officer1@example.com",
        "password": "Password123!",
        "full_name": "Officer One",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "officer1@example.com"
    assert data["full_name"] == "Officer One"
    assert data["role"] == UserRole.OFFICER.value
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_user_duplicate_email(client: AsyncClient):
    payload = {
        "email": "duplicate@example.com",
        "password": "Password123!",
        "full_name": "Duplicate User",
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_register_user_forbid_extra_role_field(client: AsyncClient):
    payload = {
        "email": "tamper@example.com",
        "password": "Password123!",
        "full_name": "Tamper User",
        "role": "ADMIN",  # Should be rejected by extra="forbid"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    reg_payload = {
        "email": "loginuser@example.com",
        "password": "Password123!",
        "full_name": "Login User",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_payload = {
        "email": "loginuser@example.com",
        "password": "Password123!",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    login_payload = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword",
    }
    response = await client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_endpoint(client: AsyncClient):
    reg_payload = {
        "email": "meuser@example.com",
        "password": "Password123!",
        "full_name": "Me User",
    }
    await client.post("/api/v1/auth/register", json=reg_payload)

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "meuser@example.com", "password": "Password123!"},
    )
    token = login_res.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    data = me_res.json()
    assert data["email"] == "meuser@example.com"
    assert data["full_name"] == "Me User"


@pytest.mark.asyncio
async def test_inactive_user_login(client: AsyncClient, db_session: AsyncSession):
    inactive_user = User(
        id=uuid.uuid4(),
        email="inactive@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Inactive User",
        role=UserRole.OFFICER,
        is_active=False,
    )
    db_session.add(inactive_user)
    await db_session.commit()

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"},
    )
    assert login_res.status_code == 401
    assert login_res.json()["detail"] == "Inactive user"
