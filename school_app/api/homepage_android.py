from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from fastapi import Request, Query
from typing import Optional
from sqlalchemy import select, or_, tuple_
from typing import List
from schemas.admin_schemas import ResultResponse, SchoolGroupCreate, SchoolStreamClassCreate,SchoolStreamCreate,SchoolStreamSubjectCreate
from models.admin_models import School, SchoolGroup, SchoolStream, SchoolStreamClass, SchoolStreamSubject, SchoolUser
from database.redis_cache import cache
from models.common_models import SchoolClassStudentMapping, TimeTable, CustomAlarm
from schemas.common_schemas import TimetableResponse,CustomAlarmCreate

# Parse date string
from datetime import datetime
from fastapi.encoders import jsonable_encoder

## ADMIN PAGE ROUTER
android_home_router = APIRouter(tags=["ANDROID API'S FOR HOME"])

@android_home_router.get("/student/dashboard/timetable", response_model=ResultResponse)
async def get_android_dashboard_info(
    student_id: int,
    target_date: str,
    db: AsyncSession = Depends(get_db),
):
    target_date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
    cache_key = f"school:{student_id}:dashboard:timetable:meta"
    res_cached = await cache.get(cache_key)
    if res_cached:
        return ResultResponse(
            code=200,
            status="Success",
            message="School dashboard data fetched successfully (cache)",
            result={
                "cache": True,
                "data": res_cached
            }
        )

    stmt = (
        select(
            TimeTable.day,
            TimeTable.start_time,
            TimeTable.end_time,
            SchoolStreamSubject.subject_name,
            SchoolStreamClass.class_name
        )
        .join(SchoolStreamClass, TimeTable.class_id == SchoolStreamClass.class_id)
        .join(SchoolStreamSubject, TimeTable.subject_id == SchoolStreamSubject.subject_id)
        .join(SchoolClassStudentMapping, SchoolClassStudentMapping.class_id == TimeTable.class_id)
        .where(
            SchoolClassStudentMapping.student_id == student_id,
            TimeTable.date == target_date_obj
        )
        .order_by(TimeTable.start_time)
    )

    result = await db.execute(stmt)
    rows = result.mappings().all()
    timetable = [TimetableResponse(**row).dict() for row in rows]
    await cache.set(cache_key, value=timetable, expire=600)

    return ResultResponse(
        code=200,
        status="Success",
        message="School dashboard data fetched successfully",
        result={"data": timetable}
    )


@android_home_router.post("/teacher/alarm", response_model=ResultResponse)
async def create_school_alarm(
    alarm: CustomAlarmCreate,
    db: AsyncSession = Depends(get_db)
):
    
    stmt = select(CustomAlarm).where(
        CustomAlarm.alarm_date == alarm.alarm_date,
        CustomAlarm.slot_time == alarm.slot_time
    )
    result = await db.execute(stmt)
    existing = result.scalars().first()
    
    if existing:
        return ResultResponse(
            code=409,
            status="Failed",
            message="Alarm already exists",
            result={}
        )

    # Alarm does not exist, insert new record
    new_alarm = CustomAlarm(
        stream_id=alarm.stream_id,
        class_id=alarm.class_id,
        message=alarm.message,
        alarm_date=alarm.alarm_date,
        slot_time=alarm.slot_time
    )
    db.add(new_alarm)
    await db.commit()
    await db.refresh(new_alarm)

    return ResultResponse(
        code=201,
        status="Success",
        message="Alarm created successfully",
        result={"alarm_id": new_alarm.id}
    )