# online_class_web.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.redis_cache import cache
from models.online_class_models import OnlineClass
from models.admin_models import SchoolStreamSubject
from schemas.online_class_schemas import OnlineClassCreate, OnlineClassUpdate
from schemas.admin_schemas import ResultResponse

online_class_web_router = APIRouter(tags=["WEB API'S ONLINE CLASS"])

def _cache_key(class_id: int) -> str:
    return f"online_class:class:{class_id}"

@online_class_web_router.post("/online-class", response_model=ResultResponse)
async def create_online_class(payload: OnlineClassCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_item = OnlineClass(school_id=payload.school_id, class_id=payload.class_id,
            subject_id=payload.subject_id, title=payload.title, meeting_link=payload.meeting_link,
            scheduled_at=payload.scheduled_at, duration_min=payload.duration_min or 60)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        await cache.delete(_cache_key(payload.class_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=201, status="Success", message="Online class created successfully",
            result={"id": new_item.id, "school_id": new_item.school_id, "class_id": new_item.class_id,
                    "title": new_item.title, "meeting_link": new_item.meeting_link,
                    "scheduled_at": new_item.scheduled_at.isoformat(), "duration_min": new_item.duration_min})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@online_class_web_router.put("/online-class/{online_class_id}", response_model=ResultResponse)
async def update_online_class(online_class_id: int, payload: OnlineClassUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(OnlineClass).where(OnlineClass.id == online_class_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Online class not found", result={})
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await db.commit()
        await db.refresh(item)
        await cache.delete(_cache_key(item.class_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Online class updated successfully",
            result={"id": item.id, "title": item.title, "meeting_link": item.meeting_link,
                    "scheduled_at": item.scheduled_at.isoformat(), "duration_min": item.duration_min})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@online_class_web_router.delete("/online-class/{online_class_id}", response_model=ResultResponse)
async def delete_online_class(online_class_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(OnlineClass).where(OnlineClass.id == online_class_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Online class not found", result={})
        class_id = item.class_id
        await db.delete(item)
        await db.commit()
        await cache.delete(_cache_key(class_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Online class deleted successfully", result={"id": online_class_id})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@online_class_web_router.get("/online-class", response_model=ResultResponse)
async def get_online_classes(
    school_id: int = Query(None, description="Filter by school ID"),
    class_id: int = Query(None, description="Filter by class ID"),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = (
            select(OnlineClass, SchoolStreamSubject.subject_name)
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == OnlineClass.subject_id)
        )
        if school_id:
            stmt = stmt.where(OnlineClass.school_id == school_id)
        if class_id:
            stmt = stmt.where(OnlineClass.class_id == class_id)
        stmt = stmt.order_by(OnlineClass.scheduled_at.desc())

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return ResultResponse(code=404, status="Failed", message="No online classes found", result={})

        data = [{"id": r[0].id, "title": r[0].title, "subject": r.subject_name or "N/A",
                 "meeting_link": r[0].meeting_link, "scheduled_at": r[0].scheduled_at.isoformat(),
                 "duration_min": r[0].duration_min, "class_id": r[0].class_id,
                 "school_id": r[0].school_id} for r in rows]

        return ResultResponse(code=200, status="Success", message="Online classes fetched successfully",
            result={"total": len(data), "data": data})
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")
