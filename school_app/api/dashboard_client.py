from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import uuid, time

from database.session import get_db
from schemas.user_schemas import DeviceRegisterRequest
from schemas.admin_schemas import ResultResponse
from models.user_models import DeviceRegistration, Session as SessionModel, FcmToken
from helper.decorators import validate_session
from helper.optmessage import _send_otp_logic, _verify_otp_logic
from schemas.user_schemas import SignIN, ChooseAccountRequest, ForceLogoutRequest
from database.redis_cache import cache
from models.student_web_models import Student, SchoolClassStudentMapping
from models.admin_models import SchoolUser, SchoolStreamClass, SchoolStream
from models.common_models import TimeTable
from models.teacher_web_models import Employee, EmployeeRoleClassSubjectMap
from models.admin_models import SchoolStreamSubject


dashboard_routers = APIRouter(tags=["CLIENT API'S DASHBOARD"])

@dashboard_routers.post(
    "/register",
    response_model=ResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register device and create session",
)
async def register_device(payload: DeviceRegisterRequest, db: AsyncSession = Depends(get_db)):

    # ── 1. Check if device already exists ────────────────────────────
    stmt = select(DeviceRegistration).where(
        DeviceRegistration.device_id == payload.device_id
    )
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if device:
        stmt = select(SessionModel).where(SessionModel.device_id == device.id)
        result = await db.execute(stmt)
        session_data = result.scalar_one_or_none()

        return ResultResponse(
            code=202,
            status="Success",
            message="Device already registered.",
            result={"client_key": session_data.client_key if session_data else None}
        )

    # ── 2. Insert new device ──────────────────────────────────────────
    device = DeviceRegistration(
        device_id   = payload.device_id,
        os          = payload.os,
        os_version  = payload.os_version,
        make        = payload.make,
        model       = payload.model,
        app_version = payload.app_version,
        fcm_token   = payload.fcm_token,
    )
    db.add(device)

    fcm = FcmToken(fcm_token=payload.fcm_token)
    db.add(fcm)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device registration conflict.")

    client_key = str(uuid.uuid5(uuid.NAMESPACE_DNS, payload.device_id + str(time.time())))
    valid_till = datetime.utcnow() + relativedelta(months=3)

    session_obj = SessionModel(
        device_id  = device.id,
        client_key = client_key,
        valid_till = valid_till,
    )
    db.add(session_obj)

    try:
        await db.commit()
        await db.refresh(device)
        await db.refresh(session_obj)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session creation conflict.")

    return ResultResponse(
        code=201,
        status="Success",
        message="Device registered successfully.",
        result={
            "client_key": session_obj.client_key,
            "valid_till": session_obj.valid_till.isoformat(),
        }
    )


@dashboard_routers.post("/session/refresh", response_model=ResultResponse)
async def refresh_session(
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    new_client_key = str(uuid.uuid4())
    new_valid_till = datetime.utcnow() + relativedelta(months=3)

    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()

    if not session_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    session_db.client_key = new_client_key
    session_db.valid_till = new_valid_till

    try:
        await db.commit()
        await db.refresh(session_db)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session refresh conflict.")

    old_cache_key = f"session:{session.client_key}"
    await cache.delete(old_cache_key)

    return ResultResponse(
        code=200,
        status="Success",
        message="Session refreshed successfully.",
        result={
            "client_key": new_client_key,
            "valid_till": new_valid_till.isoformat(),
        }
    )


# ── Helper: find all matching accounts by phone ───────────────────────────────
async def _get_accounts_by_phone(identifier: str, db: AsyncSession) -> list[dict]:
    accounts = []

    stmt = select(Student).where(Student.phone == identifier)
    result = await db.execute(stmt)
    students = result.scalars().all()
    for s in students:
        accounts.append({
            "inq_id": s.student_id,
            "role":   "student",
            "name":   f"{s.first_name} {s.last_name or ''}".strip(),
            "id":     s.student_roll_id
        })

    stmt = select(SchoolUser).where(SchoolUser.phone == identifier)
    result = await db.execute(stmt)
    users = result.scalars().all()
    for u in users:
        accounts.append({
            "inq_id": u.user_id,
            "role":   u.role,
            "name":   u.full_name,
            "id":     u.employee_id
        })

    return accounts


@dashboard_routers.post("/signin", response_model=ResultResponse)
async def sign_in(
    payload: SignIN,
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    identifier = payload.identifier
    otp        = payload.otp
    resend     = payload.resend
    fcm_token  = session.device.fcm_token if session.device else None

    accounts = await _get_accounts_by_phone(identifier, db)
    if accounts:
        for account in accounts:
            stmt = select(SessionModel).where(
                SessionModel.user_id == str(account["inq_id"]),
                SessionModel.id      != session.id
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This account is already logged in on another device. Please logout first."
                )

    if not otp and not resend:
        await _send_otp_logic(identifier=identifier, db=db, fcb_token=fcm_token)
        return ResultResponse(code=200, status="Success", message="OTP sent successfully.", result={"identifier": identifier})

    if resend:
        await _send_otp_logic(identifier=identifier, db=db, fcb_token=fcm_token)
        return ResultResponse(code=200, status="Success", message="OTP resent successfully.", result={"identifier": identifier})

    await _verify_otp_logic(identifier=identifier, otp=otp, db=db)

    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found for this phone number.")

    if len(accounts) > 1:
        return ResultResponse(code=300, status="Choose", message="Multiple accounts found. Please choose one.", result={"accounts": accounts})

    chosen_inq_id = accounts[0]["inq_id"]
    chosen_role   = accounts[0]["role"]
    chosen_id     = accounts[0]["id"]

    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = str(chosen_inq_id)
        session_db.role    = chosen_role
        await db.commit()
        await cache.delete(f"session:{session.client_key}")

    return ResultResponse(code=200, status="Success", message="Login successful.", result={"inq_id": chosen_inq_id, "role": chosen_role, "id": chosen_id})


@dashboard_routers.post("/session/forcelogout", response_model=ResultResponse)
async def force_logout(
    payload: ForceLogoutRequest,
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    accounts = await _get_accounts_by_phone(payload.identifier, db)
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found for this identifier.")

    removed = False
    for account in accounts:
        stmt = select(SessionModel).where(
            SessionModel.user_id == str(account["inq_id"]),
            SessionModel.id      != session.id
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.user_id = None
            existing.role    = None
            await db.commit()
            await cache.delete(f"session:{existing.client_key}")
            removed = True
            break

    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active session found on another device.")

    return ResultResponse(code=200, status="Success", message="Other device session removed. You can now login.", result={"identifier": payload.identifier})


@dashboard_routers.post("/signin/choose", response_model=ResultResponse)
async def choose_account(
    payload: ChooseAccountRequest,
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SessionModel).where(
        SessionModel.user_id == str(payload.inq_id),
        SessionModel.id      != session.id
    )
    result = await db.execute(stmt)
    existing_session = result.scalar_one_or_none()
    if existing_session:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This account is already logged in on another device.")

    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = str(payload.inq_id)
        session_db.role    = payload.role
        await db.commit()
        await cache.delete(f"session:{session.client_key}")

    return ResultResponse(code=200, status="Success", message="Account selected. Login successful.", result={"inq_id": payload.inq_id, "role": payload.role, "id": payload.id})


@dashboard_routers.get("/profile", response_model=ResultResponse)
async def get_profile(
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    if not session.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please sign in first.")
    if not session.user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")

    return ResultResponse(code=200, status="Success", message="Profile fetched successfully.", result=session.user)


@dashboard_routers.post("/logout", response_model=ResultResponse)
async def logout(
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = None
        await db.commit()

    await cache.delete(f"session:{session.client_key}")

    return ResultResponse(code=200, status="Success", message="Logged out successfully.", result={})

# ─────────────────────────────────────────────────────────────────────────────
# CLIENT — GET /today-classes
# Auto-detects class_id from session (student) or employee mapping (staff)
# Optional: pass ?target_date=2026-03-10 to get any day's schedule
# ─────────────────────────────────────────────────────────────────────────────
@dashboard_routers.get("/today-classes", response_model=ResultResponse)
async def get_today_classes(
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
    target_date: date = Query(default=None, description="Date to fetch classes for (default: today)"),
):
    try:
        if not session.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please sign in first.")

        # ── Use today if no date passed ───────────────────────────────
        fetch_date = target_date or date.today()
        day_name   = fetch_date.strftime("%A")  # e.g. "Tuesday"

        class_id = None

        # ── Resolve class_id based on role ────────────────────────────
        if session.role == "student":
            stmt = select(SchoolClassStudentMapping.class_id).where(
                SchoolClassStudentMapping.student_id == int(session.user_id),
                SchoolClassStudentMapping.is_active  == 1
            )
            result = await db.execute(stmt)
            class_id = result.scalar_one_or_none()

        else:
            # staff / teacher — get class from employee mapping
            stmt = select(SchoolUser).where(SchoolUser.user_id == int(session.user_id))
            result = await db.execute(stmt)
            school_user = result.scalar_one_or_none()

            if school_user:
                emp_stmt = select(EmployeeRoleClassSubjectMap.class_id).where(
                    EmployeeRoleClassSubjectMap.emp_id == int(session.user_id)
                )
                emp_result = await db.execute(emp_stmt)
                class_id = emp_result.scalar_one_or_none()

        if not class_id:
            return ResultResponse(
                code=404,
                status="Failed",
                message="No class assigned to this account.",
                result={}
            )

        # ── Cache key ─────────────────────────────────────────────────
        cache_key = f"timetable:class:{class_id}:date:{fetch_date}"
        cached = await cache.get(cache_key)
        if cached:
            return ResultResponse(
                code=200,
                status="Success",
                message=f"Today's classes fetched successfully (cache)",
                result={"cache": True, "date": str(fetch_date), "day": day_name, "classes": cached}
            )

        # ── Query timetable joined with subject ───────────────────────
        stmt = (
            select(
                TimeTable.id,
                TimeTable.start_time,
                TimeTable.end_time,
                TimeTable.duration,
                TimeTable.day,
                TimeTable.date,
                SchoolStreamSubject.subject_name,
            )
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
            .where(
                TimeTable.class_id == class_id,
                TimeTable.day == day_name
            )
            .order_by(TimeTable.start_time)
        )

        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return ResultResponse(
                code=404,
                status="Failed",
                message=f"No classes scheduled for {day_name}",
                result={"date": str(fetch_date), "day": day_name}
            )

        classes = [
            {
                "id":           row.id,
                "subject":      row.subject_name or "N/A",
                "start_time":   row.start_time.strftime("%I:%M %p") if row.start_time else None,
                "end_time":     row.end_time.strftime("%I:%M %p") if row.end_time else None,
                "duration_min": row.duration,
                "day":          row.day,
            }
            for row in rows
        ]

        await cache.set(cache_key, classes, expire=3600)

        return ResultResponse(
            code=200,
            status="Success",
            message=f"Today's classes fetched successfully",
            result={"cache": False, "date": str(fetch_date), "day": day_name, "classes": classes}
        )

    except HTTPException:
        raise
    except Exception as e:
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )
