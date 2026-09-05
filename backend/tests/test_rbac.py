import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_officer_access(client: AsyncClient, db_session: AsyncSession):
    officer_user = User(
        id=uuid.uuid4(),
        email="officer_rbac@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Officer RBAC",
        role=UserRole.OFFICER,
        is_active=True,
    )
    db_session.add(officer_user)
    await db_session.commit()

    token = create_access_token(subject=officer_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Officer accessing officer-only endpoint
    res_officer = await client.get("/api/v1/auth/officer-only", headers=headers)
    assert res_officer.status_code == 200
    assert res_officer.json()["message"] == "Officer access granted"

    # Officer attempting to access admin-only endpoint (HTTP 403)
    res_admin = await client.get("/api/v1/auth/admin-only", headers=headers)
    assert res_admin.status_code == 403
    assert res_admin.json()["detail"] == "Forbidden: insufficient permissions"


@pytest.mark.asyncio
async def test_admin_access(client: AsyncClient, db_session: AsyncSession):
    admin_user = User(
        id=uuid.uuid4(),
        email="admin_rbac@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Admin RBAC",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin_user)
    await db_session.commit()

    token = create_access_token(subject=admin_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    res_admin = await client.get("/api/v1/auth/admin-only", headers=headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["message"] == "Admin access granted"
