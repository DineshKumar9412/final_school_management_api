from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Annotated

from database.session import get_db
from models.user_models import Session as SessionModel, DeviceRegistration
from models.student_web_models import Student
from models.admin_models import SchoolUser
from database.redis_cache import cache


async def _resolve_user(user_id: str, role: str, db: AsyncSession) -> dict | None:

    if role == "student":
        stmt = select(Student).where(Student.student_id == int(user_id))
        result = await db.execute(stmt)
        student = result.scalar_one_or_none()
        if student:
            return {
                "id":     student.student_id,
                "role":   "student",
                "name":   f"{student.first_name} {student.last_name or ''}".strip(),
                "phone":  student.phone,
                "email":  student.email,
                "status": student.status,
            }

    else:  # teacher / admin / staff / instructor
        stmt = select(SchoolUser).where(SchoolUser.user_id == int(user_id))
        result = await db.execute(stmt)
        school_user = result.scalar_one_or_none()
        if school_user:
            return {
                "id":     school_user.user_id,
                "role":   school_user.role,
                "name":   school_user.full_name,
                "phone":  school_user.phone,
                "email":  school_user.email,
                "status": school_user.status,
            }

    return None

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
    
        session = SessionModel(
            id         = cached["id"],
            device_id  = cached["device_id"],
            user_id    = cached["user_id"],
            role       = cached.get("role"),
            client_key = cached["client_key"],
            valid_till = valid_till,
        )

        # Attach device from cache
        if cached.get("device"):
            session.device = DeviceRegistration(
                id        = cached["device"]["id"],
                device_id = cached["device"]["device_id"],
                fcm_token = cached["device"]["fcm_token"],
                os        = cached["device"]["os"],
                is_active = cached["device"]["is_active"],
            )

        # Attach user dict from cache
        session.user = cached.get("user")

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

    # ── 4. Resolve user if user_id + role are set ─────────────────────
    user_data = None
    if session.user_id and session.role:
        user_data = await _resolve_user(session.user_id, session.role, db)

    session.user = user_data

    # ── 5. Store in cache ─────────────────────────────────────────────
    await cache.set(
        cache_key,
        {
            "id":         session.id,
            "device_id":  session.device_id,
            "user_id":    session.user_id,
            "role":       session.role,
            "client_key": session.client_key,
            "valid_till": session.valid_till.isoformat(),
            "device": {
                "id":        session.device.id,
                "device_id": session.device.device_id,
                "fcm_token": session.device.fcm_token,
                "os":        session.device.os,
                "is_active": session.device.is_active,
            },
            "user": user_data,
        },
        expire=300
    )

    return session