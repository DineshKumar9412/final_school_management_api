
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db

from models.common_models import TimeTable
from schemas.common_schemas import TimetableCreate
from schemas.admin_schemas import ResultResponse



from fastapi import Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import Optional

from database.redis_cache import cache

time_table_router = APIRouter(tags=[" WEB API'S TIME_TABLE"])

@time_table_router.post("/time_table", response_model=ResultResponse, status_code=201)
async def create_time_table(
    payload: TimetableCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        timetable = TimeTable(
            **payload.model_dump(exclude_unset=True)
        )

        db.add(timetable)
        await db.commit()
        await db.refresh(timetable)

        return ResultResponse(
            code=201,
            status="Success",
            message="Time table created successfully",
            result={"time_table_id": timetable.id}
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    
@time_table_router.get("/get_time_table", response_model=ResultResponse)
async def get_time_table(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TimeTable))
    rows = result.scalars().all()

    data = []
    for row in rows:
        data.append({
            "start_time": row.start_time.strftime("%I:%M:%S %p"),
            "end_time": row.end_time.strftime("%I:%M:%S %p"),
            "duration": row.duration,
            "day": row.day
        })

    return ResultResponse(
        code=200,
        status="Success",
        message="Time tables fetched successfully",
        result={"data":data}
    )