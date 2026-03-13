# time_table.py — WEB only (POST/GET)
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from models.common_models import TimeTable
from models.admin_models import SchoolStreamSubject
from schemas.common_schemas import TimetableCreate
from schemas.admin_schemas import ResultResponse
from database.redis_cache import cache

time_table_router = APIRouter(tags=["WEB API'S TIME_TABLE"])


@time_table_router.post("/time_table", response_model=ResultResponse, status_code=201)
async def create_time_table(payload: TimetableCreate, db: AsyncSession = Depends(get_db)):
    try:
        timetable = TimeTable(**payload.model_dump(exclude_unset=True))
        db.add(timetable)
        await db.commit()
        await db.refresh(timetable)
        if timetable.class_id:
            await cache.delete_pattern(f"timetable:class:{timetable.class_id}:*")
            await cache.delete_pattern(f"student:*:dashboard")
        return ResultResponse(code=201, status="Success", message="Timetable created successfully",
            result={"time_table_id": timetable.id})
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@time_table_router.get("/get_time_table", response_model=ResultResponse)
async def get_time_table(
    class_id: int = Query(..., description="Class ID to filter timetable"),
    db: AsyncSession = Depends(get_db)
):
    try:
        cache_key = f"timetable:class:{class_id}:all"
        cached = await cache.get(cache_key)
        if cached:
            return ResultResponse(code=200, status="Success", message="Timetable fetched successfully (cache)",
                result={"cache": True, "data": cached})

        stmt = (
            select(TimeTable, SchoolStreamSubject.subject_name)
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
            .where(TimeTable.class_id == class_id)
            .order_by(TimeTable.day, TimeTable.start_time)
        )
        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return ResultResponse(code=404, status="Failed", message="No timetable found for this class", result={})

        data = [{"id": row[0].id, "subject": row.subject_name or "N/A", "day": row[0].day,
            "date": row[0].date.isoformat() if row[0].date else None,
            "start_time": row[0].start_time.strftime("%I:%M %p"),
            "end_time": row[0].end_time.strftime("%I:%M %p"),
            "duration_min": row[0].duration, "type": row[0].type} for row in rows]

        await cache.set(cache_key, data, expire=3600)
        return ResultResponse(code=200, status="Success", message="Timetable fetched successfully",
            result={"cache": False, "data": data})
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")
