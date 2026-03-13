# event_web.py — WEB (POST/PUT/DELETE/GET)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.redis_cache import cache
from models.event_models import SchoolEvent
from schemas.event_schemas import SchoolEventCreate, SchoolEventUpdate
from schemas.admin_schemas import ResultResponse

event_web_router = APIRouter(tags=["WEB API'S EVENT"])


def _cache_key(school_id: int) -> str:
    return f"school:{school_id}:events"


@event_web_router.post("/event", response_model=ResultResponse)
async def create_event(payload: SchoolEventCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_item = SchoolEvent(school_id=payload.school_id, title=payload.title,
            description=payload.description, status=payload.status if payload.status is not None else 1)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        await cache.delete(_cache_key(payload.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=201, status="Success", message="Event created successfully",
            result={"id": new_item.id, "school_id": new_item.school_id,
                    "title": new_item.title, "description": new_item.description, "status": new_item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


@event_web_router.put("/event/{event_id}", response_model=ResultResponse)
async def update_event(event_id: int, payload: SchoolEventUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolEvent).where(SchoolEvent.id == event_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Event not found", result={})
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await db.commit()
        await db.refresh(item)
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Event updated successfully",
            result={"id": item.id, "school_id": item.school_id,
                    "title": item.title, "description": item.description, "status": item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


@event_web_router.delete("/event/{event_id}", response_model=ResultResponse)
async def delete_event(event_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolEvent).where(SchoolEvent.id == event_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Event not found", result={})
        item.status = 0
        await db.commit()
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Event deleted successfully", result={"id": event_id})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


@event_web_router.get("/event", response_model=ResultResponse)
async def get_events(
    school_id: int = Query(..., description="School ID"),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolEvent).where(
            SchoolEvent.school_id == school_id
        ).order_by(SchoolEvent.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()

        if not items:
            return ResultResponse(code=404, status="Failed", message="No events found", result={})

        data = [{"id": i.id, "title": i.title, "description": i.description,
                 "status": i.status, "created_at": i.created_at.isoformat()} for i in items]

        return ResultResponse(code=200, status="Success", message="Events fetched successfully",
            result={"total": len(data), "data": data})
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")
