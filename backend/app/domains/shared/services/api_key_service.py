"""API key lifecycle: generation, verification, and management."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.shared.models.api_key import ApiKey

_KEY_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_KEY_RANDOM_LEN = 43


def _hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ApiKeyService:
    """CRUD + verification for open-API keys (hash-only storage)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_key(
        self,
        key_name: str,
        scopes: list[str],
        created_by: int | None = None,
        rate_limit_per_minute: int | None = None,
        expires_at: datetime | None = None,
    ) -> dict:
        """Create a key. Returns {"record": ApiKey, "key": plaintext-once}."""
        plaintext = "ak_" + "".join(secrets.choice(_KEY_ALPHABET) for _ in range(_KEY_RANDOM_LEN))
        record = ApiKey(
            key_name=key_name,
            key_hash=_hash_key(plaintext),
            key_prefix=plaintext[:8],
            scopes=sorted(set(scopes)),
            rate_limit_per_minute=rate_limit_per_minute,
            expires_at=expires_at,
            created_by=created_by,
        )
        self.session.add(record)
        await self.session.flush()
        return {"record": record, "key": plaintext}

    async def verify_key(self, plaintext: str) -> ApiKey | None:
        """Return the active, unexpired key record, or None. Touches last_used_at."""
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.key_hash == _hash_key(plaintext))
        )
        record = result.scalar_one_or_none()
        if record is None or not record.is_active:
            return None
        if record.expires_at is not None and record.expires_at <= _now():
            return None
        await self.session.execute(
            update(ApiKey)
            .where(ApiKey.api_key_id == record.api_key_id)
            .values(last_used_at=_now())
        )
        return record

    @staticmethod
    def has_scope(record: ApiKey, scope: str) -> bool:
        return scope in (record.scopes or [])

    async def set_active(self, api_key_id: int, is_active: bool) -> None:
        await self.session.execute(
            update(ApiKey).where(ApiKey.api_key_id == api_key_id).values(is_active=is_active)
        )

    async def list_keys(self) -> list[ApiKey]:
        result = await self.session.execute(select(ApiKey).order_by(ApiKey.api_key_id.desc()))
        return list(result.scalars().all())

    async def get_by_id(self, api_key_id: int) -> ApiKey | None:
        result = await self.session.execute(
            select(ApiKey).where(ApiKey.api_key_id == api_key_id)
        )
        return result.scalar_one_or_none()
