"""API key management endpoints (super_admin only)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_access_token, hash_password
from app.domains.shared.models.enums import UserRoleType
from app.domains.shared.models.iam import UserAccount


async def _seed_user(session: AsyncSession, username: str, role: str) -> UserAccount:
    user = UserAccount(
        username=username,
        email=f"{username}@example.com",
        password_hash=hash_password("pass1234"),
        role_type=role,
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


def _token(user: UserAccount) -> str:
    return create_access_token(
        user_id=user.user_id, username=user.username, role=user.role_type
    )


@pytest.mark.asyncio
async def test_create_list_revoke_flow(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    admin = await _seed_user(test_session, "ak_admin", UserRoleType.SUPER_ADMIN.value)
    await test_session.commit()
    headers = {"Authorization": f"Bearer {_token(admin)}"}

    r = await client.post(
        "/api/v1/api-keys",
        headers=headers,
        json={"key_name": "洞察 Skill", "scopes": ["academic:read", "industry:write"]},
    )
    assert r.status_code == 200, r.text
    created = r.json()
    assert created["plaintext_key"].startswith("ak_")
    assert created["key_prefix"] == created["plaintext_key"][:8]

    listed = (await client.get("/api/v1/api-keys", headers=headers)).json()
    assert any(k["api_key_id"] == created["api_key_id"] for k in listed)
    item = next(k for k in listed if k["api_key_id"] == created["api_key_id"])
    assert "plaintext_key" not in item  # 列表永不返回明文
    assert set(item["scopes"]) == {"academic:read", "industry:write"}

    revoked = await client.patch(
        f"/api/v1/api-keys/{created['api_key_id']}",
        headers=headers,
        json={"is_active": False},
    )
    assert revoked.status_code == 200
    listed2 = (await client.get("/api/v1/api-keys", headers=headers)).json()
    item2 = next(k for k in listed2 if k["api_key_id"] == created["api_key_id"])
    assert item2["is_active"] is False


@pytest.mark.asyncio
async def test_key_management_forbidden_for_user(
    client: AsyncClient, test_session: AsyncSession
) -> None:
    user = await _seed_user(test_session, "ak_plain", UserRoleType.USER.value)
    await test_session.commit()
    r = await client.get(
        "/api/v1/api-keys", headers={"Authorization": f"Bearer {_token(user)}"}
    )
    assert r.status_code == 403
