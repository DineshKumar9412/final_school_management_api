# online_class_web.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.redis_cache import cache
from models.online_class_models import OnlineClass
from models.admin_models import SchoolStreamSubject
from schemas.online_class_schemas import OnlineClassCreate, OnlineClassUpdate
from schemas.admin_schemas import ResultResponse


# ── Web Routes (Admin/School team) ────────────────────────────────────────────
online_class_web_router = APIRouter(tags=["WEB API'S ONLINE CLASS"])

# ── Client Routes (Android/iOS team) ──────────────────────────────────────────
online_class_client_router = APIRouter(tags=["CLIENT API'S DASHBOARD"])


def _cache_key(class_id: int) -> str:
    return f"online_class:class:{class_id}"


# ─────────────────────────────────────────────────────────────────────────────
# WEB — POST /online-class
# ─────────────────────────────────────────────────────────────────────────────
@online_class_web_router.post("/online-class", response_model=ResultResponse)
async def create_online_class(
    payload: OnlineClassCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_class = OnlineClass(
            school_id    = payload.school_id,
            class_id     = payload.class_id,
            subject_id   = payload.subject_id,
            title        = payload.title,
            meeting_link = payload.meeting_link,
            scheduled_at = payload.scheduled_at,
            duration_min = payload.duration_min or 60,
        )
        db.add(new_class)
        await db.commit()
        await db.refresh(new_class)

        await cache.delete(_cache_key(payload.class_id))

        return ResultResponse(
            code=201,
            status="Success",
            message="Online class created successfully",
            result={
                "id":           new_class.id,
                "school_id":    new_class.school_id,
                "class_id":     new_class.class_id,
                "subject_id":   new_class.subject_id,
                "title":        new_class.title,
                "meeting_link": new_class.meeting_link,
                "scheduled_at": new_class.scheduled_at.isoformat(),
                "duration_min": new_class.duration_min,
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# WEB — PUT /online-class/{id}
# ─────────────────────────────────────────────────────────────────────────────
@online_class_web_router.put("/online-class/{online_class_id}", response_model=ResultResponse)
async def update_online_class(
    online_class_id: int,
    payload: OnlineClassUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(OnlineClass).where(OnlineClass.id == online_class_id)
        result = await db.execute(stmt)
        online_class = result.scalar_one_or_none()

        if not online_class:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Online class not found",
                result={}
            )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(online_class, key, value)

        await db.commit()
        await db.refresh(online_class)

        await cache.delete(_cache_key(online_class.class_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Online class updated successfully",
            result={
                "id":           online_class.id,
                "title":        online_class.title,
                "meeting_link": online_class.meeting_link,
                "scheduled_at": online_class.scheduled_at.isoformat(),
                "duration_min": online_class.duration_min,
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# WEB — DELETE /online-class/{id}  → hard delete
# ─────────────────────────────────────────────────────────────────────────────
@online_class_web_router.delete("/online-class/{online_class_id}", response_model=ResultResponse)
async def delete_online_class(
    online_class_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(OnlineClass).where(OnlineClass.id == online_class_id)
        result = await db.execute(stmt)
        online_class = result.scalar_one_or_none()

        if not online_class:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Online class not found",
                result={}
            )

        class_id = online_class.class_id

        await db.delete(online_class)  # ✅ hard delete
        await db.commit()

        await cache.delete(_cache_key(class_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Online class deleted successfully",
            result={"id": online_class_id}
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT — GET /online-class?class_id=
# ─────────────────────────────────────────────────────────────────────────────
@online_class_client_router.get("/online-class", response_model=ResultResponse)
async def get_online_classes(
    class_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        ck = _cache_key(class_id)
        cached = await cache.get(ck)
        if cached:
            return ResultResponse(
                code=200,
                status="Success",
                message="Online classes fetched successfully (cache)",
                result={"cache": True, "data": cached}
            )

        stmt = (
            select(
                OnlineClass,
                SchoolStreamSubject.subject_name,
            )
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == OnlineClass.subject_id)
            .where(OnlineClass.class_id == class_id)
            .order_by(OnlineClass.scheduled_at)
        )

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return ResultResponse(
                code=404,
                status="Failed",
                message="No online classes found",
                result={}
            )

        data = [
            {
                "id":           row[0].id,
                "title":        row[0].title,
                "subject":      row.subject_name or "N/A",
                "meeting_link": row[0].meeting_link,
                "scheduled_at": row[0].scheduled_at.isoformat(),
                "duration_min": row[0].duration_min,
            }
            for row in rows
        ]

        await cache.set(ck, data, expire=600)

        return ResultResponse(
            code=200,
            status="Success",
            message="Online classes fetched successfully",
            result={"cache": False, "data": data}
        )

    except Exception as e:
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )
