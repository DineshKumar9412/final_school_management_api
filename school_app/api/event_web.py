# event_web.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.redis_cache import cache
from models.event_models import SchoolEvent
from schemas.event_schemas import SchoolEventCreate, SchoolEventUpdate
from schemas.admin_schemas import ResultResponse


event_web_router = APIRouter(tags=["WEB API'S EVENT"])
event_client_router = APIRouter(tags=["CLIENT API'S DASHBOARD"])


def _cache_key(school_id: int) -> str:
    return f"school:{school_id}:events"

@event_web_router.post("/event", response_model=ResultResponse)
async def create_event(
    payload: SchoolEventCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_event = SchoolEvent(
            school_id=payload.school_id,
            title=payload.title,
            description=payload.description,
            status=payload.status if payload.status is not None else 1
        )
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)

        await cache.delete(_cache_key(payload.school_id))

        return ResultResponse(
            code=201,
            status="Success",
            message="Event created successfully",
            result={
                "id": new_event.id,
                "school_id": new_event.school_id,
                "title": new_event.title,
                "description": new_event.description,
                "status": new_event.status
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )

@event_web_router.put("/event/{event_id}", response_model=ResultResponse)
async def update_event(
    event_id: int,
    payload: SchoolEventUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolEvent).where(SchoolEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Event not found",
                result={}
            )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(event, key, value)

        await db.commit()
        await db.refresh(event)

        await cache.delete(_cache_key(event.school_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Event updated successfully",
            result={
                "id": event.id,
                "school_id": event.school_id,
                "title": event.title,
                "description": event.description,
                "status": event.status
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )

@event_web_router.delete("/event/{event_id}", response_model=ResultResponse)
async def delete_event(
    event_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolEvent).where(SchoolEvent.id == event_id)
        result = await db.execute(stmt)
        event = result.scalar_one_or_none()

        if not event:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Event not found",
                result={}
            )

        event.status = 0  # soft delete
        await db.commit()

        await cache.delete(_cache_key(event.school_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Event deleted successfully",
            result={"id": event_id}
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )

@event_client_router.get("/event", response_model=ResultResponse)
async def get_events(
    school_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        ck = _cache_key(school_id)
        cached = await cache.get(ck)
        if cached:
            return ResultResponse(
                code=200,
                status="Success",
                message="Events fetched successfully (cache)",
                result={"cache": True, "data": cached}
            )

        stmt = select(SchoolEvent).where(
            SchoolEvent.school_id == school_id,
            SchoolEvent.status == 1
        ).order_by(SchoolEvent.created_at.desc())

        result = await db.execute(stmt)
        events = result.scalars().all()

        if not events:
            return ResultResponse(
                code=404,
                status="Failed",
                message="No events found",
                result={}
            )

        data = [
            {
                "id": e.id,
                "title": e.title,
                "description": e.description,
                "created_at": e.created_at.isoformat()
            }
            for e in events
        ]

        await cache.set(ck, data, expire=600)

        return ResultResponse(
            code=200,
            status="Success",
            message="Events fetched successfully",
            result={"cache": False, "data": data}
        )

    except Exception as e:
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )
