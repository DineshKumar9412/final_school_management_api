from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from models.common_models import Notification,EmployeeAttendance,StudentAttendance

from schemas.common_schemas import NotificationCreate,EmployeeAttendanceCreate,StudentAttendanceCreate,StudentAttendanceBulkCreate,EmployeeAttendanceBulkCreate
from schemas.admin_schemas import ResultResponse

common_router = APIRouter(tags=["WEB API'S COMMON"])

from database.redis_cache import cache

@common_router.post("/notifications", response_model=ResultResponse)
async def create_notification(
    payload: NotificationCreate,
    db: AsyncSession = Depends(get_db),
):
    try:
        notification = Notification(
            title=payload.title,
            message=payload.message,
            role_id=payload.role_id,
            image=payload.image,
        )

        db.add(notification)
        await db.commit()
        await db.refresh(notification)

        return ResultResponse(
            code=201,
            status="Success",
            message="Notification created successfully",
            result={
                "id": notification.id,
                "title": notification.title,
                "message": notification.message,
                "role_id": notification.role_id
            },
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal Server Error: {str(e)}"
        )

@common_router.post("/employee/attendance/bulk",response_model=ResultResponse)
async def create_bulk_employee_attendance(
    payload: EmployeeAttendanceBulkCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        created = []
        skipped = []

        for emp in payload.employees:
            # 🔹 Prevent duplicate attendance
            exists = await db.scalar(
                select(EmployeeAttendance.att_id).where(
                    EmployeeAttendance.emp_id == emp.emp_id,
                    EmployeeAttendance.attendance_dt == payload.attendance_dt
                )
            )
            if exists:
                skipped.append(emp.emp_id)
                continue
            
            attendance = EmployeeAttendance(
                school_group_id=payload.school_group_id,
                emp_id=emp.emp_id,
                attendance_dt=payload.attendance_dt,
                status=emp.status if emp.status is not None else None
            )

            db.add(attendance)
            created.append(emp.emp_id)
            
        if not created:
            return ResultResponse(
                code=409,
                status="failed",
                message="Attendance already exists for all employees",
                result={"skipped": skipped}
            )

        await db.commit()

        return ResultResponse(
            code=201,
            status="success",
            message="Employee attendance created successfully",
            result={
                "created": created,
                "skipped": skipped
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )
        

@common_router.post("/student/attendance/bulk",response_model=ResultResponse)
async def create_bulk_student_attendance(
    payload: StudentAttendanceBulkCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        created = []
        skipped = []

        for student in payload.students:
            # 🔹 Check duplicate attendance
            exists = await db.scalar(
                select(StudentAttendance.att_id).where(
                    StudentAttendance.student_id == student.student_id,
                    StudentAttendance.attendance_dt == payload.attendance_dt
                )
            )

            if exists:
                skipped.append(student.student_id)
                continue

            attendance = StudentAttendance(
                class_id=payload.class_id,
                section=payload.section,
                school_group_id=payload.school_group_id,
                student_id=student.student_id,
                attendance_dt=payload.attendance_dt,
                status=student.status
            )

            db.add(attendance)
            created.append(student.student_id)

        if not created:
            return ResultResponse(
                code=409,
                status="failed",
                message="Attendance already exists for all students",
                result={"skipped": skipped}
            )

        await db.commit()

        return ResultResponse(
            code=201,
            status="success",
            message="Student attendance created successfully",
            result={
                "created": created,
                "skipped": skipped
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )
        
# @common_router.post("student/attendance",response_model=ResultResponse)
async def create_student_attendance(
    payload: StudentAttendanceCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 🔹 Prevent duplicate attendance for same day
        exists = await db.scalar(
            select(StudentAttendance.att_id).where(
                StudentAttendance.student_id == payload.student_id,
                StudentAttendance.attendance_dt == payload.attendance_dt
            )
        )

        if exists:
            return ResultResponse(
                code=409,
                status="failed",
                message="Attendance already marked for this date",
                result={
                    "student_id": payload.student_id,
                    "attendance_dt": payload.attendance_dt
                }
            )

        attendance = StudentAttendance(**payload.model_dump())
        db.add(attendance)

        await db.commit()
        await db.refresh(attendance)

        return ResultResponse(
            code=201,
            status="success",
            message="Student attendance created successfully",
            result={
                "att_id": attendance.att_id,
                "student_id": attendance.student_id,
                "attendance_dt": attendance.attendance_dt,
                "status": attendance.status
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )

