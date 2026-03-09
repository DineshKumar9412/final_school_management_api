from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Annotated

from database.session import get_db
from models.user_models import Session as SessionModel, DeviceRegistration
from database.redis_cache import cache


async def validate_session(
    client_key: Annotated[str, Header(description="Client key from device registration")],
    db: AsyncSession = Depends(get_db),
) -> SessionModel:

    cache_key = f"session:{client_key}"

    # ── 1. Check cache first ──────────────────────────────────────────
    cached = await cache.get(cache_key)
    if cached:
        valid_till = datetime.fromisoformat(cached["valid_till"])

        if valid_till < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired. Please re-register your device."
            )

        # ── Rebuild session + attach device from cached data ──────────
        session = SessionModel(
            id         = cached["id"],
            device_id  = cached["device_id"],
            user_id    = cached["user_id"],
            client_key = cached["client_key"],
            valid_till = valid_till,
        )

        # Attach device object from cached device fields ✅
        if cached.get("device"):
            session.device = DeviceRegistration(
                id        = cached["device"]["id"],
                device_id = cached["device"]["device_id"],
                fcm_token = cached["device"]["fcm_token"],
                os        = cached["device"]["os"],
                is_active = cached["device"]["is_active"],
            )

        return session

    # ── 2. Cache miss — query DB ──────────────────────────────────────
    stmt = (
        select(SessionModel)
        .options(selectinload(SessionModel.device))
        .where(SessionModel.client_key == client_key)
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid client key."
        )

    # ── 3. Check expiry ───────────────────────────────────────────────
    if session.valid_till < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please re-register your device."
        )

    # ── 4. Store session + device in cache ────────────────────────────
    await cache.set(
        cache_key,
        {
            "id":         session.id,
            "device_id":  session.device_id,
            "user_id":    session.user_id,
            "client_key": session.client_key,
            "valid_till": session.valid_till.isoformat(),
            "device": {
                "id":        session.device.id,
                "device_id": session.device.device_id,
                "fcm_token": session.device.fcm_token,
                "os":        session.device.os,
                "is_active": session.device.is_active,
            }
        },
        expire=300
    )

    return session