from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, Date
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
from models.admin_models import SchoolUser, SchoolStreamClass, SchoolStream, SchoolStreamSubject
from models.common_models import TimeTable, Holiday, EmployeeAttendance
from models.teacher_web_models import Employee, EmployeeRoleClassSubjectMap
from models.gallery_models import SchoolGallery
from models.banner_models import SchoolBanner
from models.event_models import SchoolEvent
from models.notice_models import SchoolNotice
from models.online_class_models import OnlineClass


dashboard_routers = APIRouter(tags=["CLIENT API'S DASHBOARD"])

async def _update_fcm_token_user_info(
    fcm_token_str: str | None,
    user_id: int,
    role: str,
    db: AsyncSession
):
    """
    After login, find the fcm_token row by device's fcm_token string
    and fill in user_id, role, class_id, section_id.

    - student  → class_id from school_class_student_mapping, section_id = class_id (no separate section table)
    - teacher/staff/admin → class_id from employee_role_class_subject_map, section_id = None
    """
    if not fcm_token_str:
        return

    fcm_result = await db.execute(
        select(FcmToken).where(FcmToken.fcm_token == fcm_token_str)
    )
    fcm_row = fcm_result.scalar_one_or_none()
    if not fcm_row:
        return

    class_id   = None
    section_id = None

    if role == "student":
        mapping_result = await db.execute(
            select(SchoolClassStudentMapping.class_id).where(
                SchoolClassStudentMapping.student_id == user_id,
                SchoolClassStudentMapping.is_active == 1
            )
        )
        class_id   = mapping_result.scalar_one_or_none()
        section_id = class_id  # no separate section table; class_id acts as section

    else:
        # teacher / staff / admin
        emp_result = await db.execute(
            select(EmployeeRoleClassSubjectMap.class_id).where(
                EmployeeRoleClassSubjectMap.emp_id == user_id
            )
        )
        class_id = emp_result.scalar_one_or_none()

    fcm_row.user_id    = user_id
    fcm_row.role       = role
    fcm_row.class_id   = class_id
    fcm_row.section_id = section_id

    await db.commit()

async def _clear_fcm_token_user_info(
    fcm_token_str: str | None,
    db: AsyncSession
):
    if not fcm_token_str:
        return

    fcm_result = await db.execute(
        select(FcmToken).where(FcmToken.fcm_token == fcm_token_str)
    )
    fcm_row = fcm_result.scalar_one_or_none()
    if not fcm_row:
        return

    # Clear user-specific fields; keep fcm_token intact
    fcm_row.user_id    = None
    fcm_row.role       = None
    fcm_row.class_id   = None
    fcm_row.section_id = None

    await db.commit()


@dashboard_routers.post(
    "/register",
    response_model=ResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register device and create session",
)
async def register_device(payload: DeviceRegisterRequest, db: AsyncSession = Depends(get_db)):

    stmt = select(DeviceRegistration).where(DeviceRegistration.device_id == payload.device_id)
    result = await db.execute(stmt)
    device = result.scalar_one_or_none()

    if device:
        # ── Update FCM token if client sends a new one ──────────────────────
        if payload.fcm_token and device.fcm_token != payload.fcm_token:
            old_fcm = device.fcm_token

            device.fcm_token = payload.fcm_token

            if old_fcm:
                fcm_stmt = select(FcmToken).where(FcmToken.fcm_token == old_fcm)
                fcm_result = await db.execute(fcm_stmt)
                fcm_row = fcm_result.scalar_one_or_none()
                if fcm_row:
                    fcm_row.fcm_token = payload.fcm_token
                else:
                    db.add(FcmToken(fcm_token=payload.fcm_token))
            else:
                db.add(FcmToken(fcm_token=payload.fcm_token))

            await db.commit()
            await db.refresh(device)

        # ── Return existing session client_key ──────────────────────────────
        session_stmt = select(SessionModel).where(SessionModel.device_id == device.id)
        session_result = await db.execute(session_stmt)
        session_data = session_result.scalar_one_or_none()

        return ResultResponse(
            code=202, status="Success",
            message="Device already registered.",
            result={"client_key": session_data.client_key if session_data else None}
        )

    # ── Purge expired sessions before inserting a new one ───────────────────
    expired_result = await db.execute(
        select(SessionModel).where(SessionModel.valid_till < datetime.utcnow())
    )
    expired_sessions = expired_result.scalars().all()
    for expired in expired_sessions:
        await cache.delete(f"session:{expired.client_key}")
        await db.delete(expired)
    if expired_sessions:
        await db.flush()

    device = DeviceRegistration(
        device_id=payload.device_id, os=payload.os, os_version=payload.os_version,
        make=payload.make, model=payload.model, app_version=payload.app_version,
        fcm_token=payload.fcm_token,
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
    session_obj = SessionModel(device_id=device.id, client_key=client_key, valid_till=valid_till)
    db.add(session_obj)

    try:
        await db.commit()
        await db.refresh(device)
        await db.refresh(session_obj)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Session creation conflict.")

    return ResultResponse(code=201, status="Success", message="Device registered successfully.",
        result={"client_key": session_obj.client_key, "valid_till": session_obj.valid_till.isoformat()})


@dashboard_routers.post("/session/refresh", response_model=ResultResponse)
async def refresh_session(session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db)):
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

    await cache.delete(f"session:{session.client_key}")

    return ResultResponse(code=200, status="Success", message="Session refreshed successfully.",
        result={"client_key": new_client_key, "valid_till": new_valid_till.isoformat()})


async def _get_accounts_by_phone(identifier: str, db: AsyncSession) -> list[dict]:
    accounts = []
    stmt = select(Student).where(Student.phone == identifier)
    result = await db.execute(stmt)
    for s in result.scalars().all():
        accounts.append({"inq_id": s.student_id, "role": "student",
            "name": f"{s.first_name} {s.last_name or ''}".strip(), "id": s.student_roll_id})

    stmt = select(SchoolUser).where(SchoolUser.phone == identifier)
    result = await db.execute(stmt)
    for u in result.scalars().all():
        accounts.append({"inq_id": u.user_id, "role": u.role, "name": u.full_name, "id": u.employee_id})

    return accounts


@dashboard_routers.post("/signin", response_model=ResultResponse)
async def sign_in(payload: SignIN, session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db)):
    identifier = payload.identifier
    otp        = payload.otp
    resend     = payload.resend
    fcm_token  = session.device.fcm_token if session.device else None

    accounts = await _get_accounts_by_phone(identifier, db)
    if accounts:
        for account in accounts:
            stmt = select(SessionModel).where(SessionModel.user_id == str(account["inq_id"]), SessionModel.id != session.id)
            result = await db.execute(stmt)
            if result.scalar_one_or_none():
                return ResultResponse(code=400, status="FAILED", message="This account is already logged in on another device. Please logout first.", result={})

    if not otp and not resend:
        await _send_otp_logic(identifier=identifier, db=db, fcb_token=fcm_token)
        return ResultResponse(code=200, status="Success", message="OTP sent successfully.", result={"identifier": identifier})

    if resend:
        await _send_otp_logic(identifier=identifier, db=db, fcb_token=fcm_token)
        return ResultResponse(code=200, status="Success", message="OTP resent successfully.", result={"identifier": identifier})

    await _verify_otp_logic(identifier=identifier, otp=otp, db=db)

    if not accounts:
        return ResultResponse(code=400, status="FAILED", message="No account found for this phone number.", result={})

    if len(accounts) > 1:
        return ResultResponse(code=300, status="Choose", message="Multiple accounts found. Please choose one.", result={"accounts": accounts})

    chosen_inq_id = accounts[0]["inq_id"]
    chosen_role   = accounts[0]["role"]
    chosen_id     = accounts[0]["id"]

    # ── Update session table ────────────────────────────────────────────────
    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = str(chosen_inq_id)
        session_db.role    = chosen_role
        await db.commit()
        await cache.delete(f"session:{session.client_key}")

    # ── Update fcm_token table with user details ────────────────────────────
    await _update_fcm_token_user_info(
        fcm_token_str=fcm_token,
        user_id=chosen_inq_id,
        role=chosen_role,
        db=db
    )

    return ResultResponse(code=200, status="Success", message="Login successful.",
        result={"inq_id": chosen_inq_id, "role": chosen_role, "id": chosen_id})


@dashboard_routers.post("/session/forcelogout", response_model=ResultResponse)
async def force_logout(payload: ForceLogoutRequest, session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db)):
    accounts = await _get_accounts_by_phone(payload.identifier, db)
    if not accounts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No account found for this identifier.")

    removed = False
    for account in accounts:
        stmt = select(SessionModel).where(SessionModel.user_id == str(account["inq_id"]), SessionModel.id != session.id)
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

    return ResultResponse(code=200, status="Success", message="Other device session removed. You can now login.",
        result={"identifier": payload.identifier})


@dashboard_routers.post("/signin/choose", response_model=ResultResponse)
async def choose_account(payload: ChooseAccountRequest, session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db)):
    stmt = select(SessionModel).where(SessionModel.user_id == str(payload.inq_id), SessionModel.id != session.id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This account is already logged in on another device.")

    # ── Update session table ────────────────────────────────────────────────
    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = str(payload.inq_id)
        session_db.role    = payload.role
        await db.commit()
        await cache.delete(f"session:{session.client_key}")

    # ── Update fcm_token table with user details ────────────────────────────
    fcm_token = session.device.fcm_token if session.device else None
    await _update_fcm_token_user_info(
        fcm_token_str=fcm_token,
        user_id=payload.inq_id,
        role=payload.role,
        db=db
    )

    return ResultResponse(code=200, status="Success", message="Account selected. Login successful.",
        result={"inq_id": payload.inq_id, "role": payload.role, "id": payload.id})


@dashboard_routers.get("/profile", response_model=ResultResponse)
async def get_profile(session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db)):
    if not session.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please sign in first.")
    if not session.user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return ResultResponse(code=200, status="Success", message="Profile fetched successfully.", result=session.user)


@dashboard_routers.post("/logout", response_model=ResultResponse)
async def logout(session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db)):
    fcm_token = session.device.fcm_token if session.device else None

    # ── Clear user_id from session ──────────────────────────────────────────
    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = None
        session_db.role    = None
        await db.commit()

    # ── Clear user details from fcm_token table ─────────────────────────────
    # Token string kept intact — device is still registered
    await _clear_fcm_token_user_info(fcm_token_str=fcm_token, db=db)

    await cache.delete(f"session:{session.client_key}")
    return ResultResponse(code=200, status="Success", message="Logged out successfully.", result={})


@dashboard_routers.get("/today-classes", response_model=ResultResponse)
async def get_today_classes(session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db),
    target_date: date = Query(default=None)):
    try:
        if not session.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please sign in first.")

        fetch_date = target_date or date.today()
        day_name   = fetch_date.strftime("%A")
        class_id   = None

        if session.role == "student":
            stmt = select(SchoolClassStudentMapping.class_id).where(
                SchoolClassStudentMapping.student_id == int(session.user_id),
                SchoolClassStudentMapping.is_active == 1)
            result = await db.execute(stmt)
            class_id = result.scalar_one_or_none()
        else:
            stmt = select(SchoolUser).where(SchoolUser.user_id == int(session.user_id))
            result = await db.execute(stmt)
            school_user = result.scalar_one_or_none()
            if school_user:
                emp_stmt = select(EmployeeRoleClassSubjectMap.class_id).where(
                    EmployeeRoleClassSubjectMap.emp_id == int(session.user_id))
                emp_result = await db.execute(emp_stmt)
                class_id = emp_result.scalar_one_or_none()

        if not class_id:
            return ResultResponse(code=404, status="Failed", message="No class assigned.", result={})

        cache_key = f"timetable:class:{class_id}:date:{fetch_date}"
        cached = await cache.get(cache_key)
        if cached:
            return ResultResponse(code=200, status="Success", message="Today's classes fetched (cache)",
                result={"cache": True, "date": str(fetch_date), "day": day_name, "classes": cached})

        stmt = (select(TimeTable.id, TimeTable.start_time, TimeTable.end_time, TimeTable.duration,
                TimeTable.day, TimeTable.date, SchoolStreamSubject.subject_name)
            .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
            .where(TimeTable.class_id == class_id, TimeTable.day == day_name)
            .order_by(TimeTable.start_time))
        result = await db.execute(stmt)
        rows = result.all()

        if not rows:
            return ResultResponse(code=404, status="Failed", message=f"No classes for {day_name}",
                result={"date": str(fetch_date), "day": day_name})

        classes = [{"id": r.id, "subject": r.subject_name or "N/A",
            "start_time": r.start_time.strftime("%I:%M %p") if r.start_time else None,
            "end_time": r.end_time.strftime("%I:%M %p") if r.end_time else None,
            "duration_min": r.duration, "day": r.day} for r in rows]

        await cache.set(cache_key, classes, expire=3600)
        return ResultResponse(code=200, status="Success", message="Today's classes fetched",
            result={"cache": False, "date": str(fetch_date), "day": day_name, "classes": classes})

    except HTTPException:
        raise
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


@dashboard_routers.get("/teacher-dashboard", response_model=ResultResponse)
async def get_teacher_dashboard(session: SessionModel = Depends(validate_session), db: AsyncSession = Depends(get_db)):
    try:
        if not session.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please sign in first.")
        if session.role not in ("teacher", "staff", "admin"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Teachers only.")

        today    = date.today()
        day_name = today.strftime("%A")
        school_id = None
        class_id  = None

        stmt = select(SchoolUser).where(SchoolUser.user_id == int(session.user_id))
        result = await db.execute(stmt)
        school_user = result.scalar_one_or_none()
        if school_user:
            school_id = school_user.school_id
            emp_stmt = select(EmployeeRoleClassSubjectMap.class_id).where(
                EmployeeRoleClassSubjectMap.emp_id == int(session.user_id))
            emp_result = await db.execute(emp_stmt)
            class_id = emp_result.scalar_one_or_none()

        total_students = (await db.execute(select(func.count()).select_from(Student).where(Student.status == 1))).scalar() or 0

        timetable = []
        if class_id:
            tt_stmt = (select(TimeTable.id, TimeTable.start_time, TimeTable.end_time,
                    TimeTable.duration, TimeTable.day, SchoolStreamSubject.subject_name)
                .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
                .where(TimeTable.class_id == class_id, TimeTable.day == day_name)
                .order_by(TimeTable.start_time))
            tt_rows = (await db.execute(tt_stmt)).all()
            timetable = [{"id": r.id, "subject": r.subject_name or "N/A",
                "start_time": r.start_time.strftime("%I:%M %p") if r.start_time else None,
                "end_time": r.end_time.strftime("%I:%M %p") if r.end_time else None,
                "duration_min": r.duration, "day": r.day} for r in tt_rows]

        absent_rows = (await db.execute(select(EmployeeAttendance).where(
            EmployeeAttendance.attendance_dt == today, EmployeeAttendance.status == "A"))).scalars().all()
        leaves = {"message": "Everyone is present today" if not absent_rows else f"{len(absent_rows)} staff absent today",
            "absent_count": len(absent_rows)}

        holiday_rows = (await db.execute(select(Holiday).where(Holiday.holiday_date >= today)
            .order_by(Holiday.holiday_date.asc()).limit(5))).scalars().all()
        holidays = [{"id": h.id, "title": h.title, "description": h.description,
            "holiday_date": h.holiday_date.isoformat(),
            "day": h.holiday_date.strftime("%d"), "month": h.holiday_date.strftime("%b")} for h in holiday_rows]

        gallery = []
        if school_id:
            gallery_rows = (await db.execute(select(SchoolGallery).where(
                SchoolGallery.school_id == school_id, SchoolGallery.status == 1)
                .order_by(SchoolGallery.created_at.desc()).limit(6))).scalars().all()
            gallery = [{"id": g.id, "bannerlink": g.bannerlink} for g in gallery_rows]

        return ResultResponse(code=200, status="Success", message="Teacher dashboard fetched successfully",
            result={"overview": {"total_students": total_students},
                "timetable": {"date": str(today), "day": day_name, "classes": timetable},
                "leaves": leaves, "holidays": holidays, "gallery": gallery})

    except HTTPException:
        raise
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


@dashboard_routers.get("/student-dashboard", response_model=ResultResponse)
async def get_student_dashboard(
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    try:
        if not session.user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please sign in first.")
        if session.role != "student":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied. Students only.")

        student_id = int(session.user_id)
        today      = date.today()
        day_name   = today.strftime("%A")

        cache_key = f"student:{student_id}:dashboard"
        cached = await cache.get(cache_key)
        if cached:
            return ResultResponse(code=200, status="Success",
                message="Student dashboard fetched successfully (cache)",
                result={"cache": True, **cached})

        profile = {}
        school_id = None
        class_id  = None

        stmt = (
            select(Student, SchoolStreamClass.class_name, SchoolStreamClass.class_code,
                   SchoolStream.stream_name, SchoolClassStudentMapping.class_id)
            .join(SchoolClassStudentMapping, SchoolClassStudentMapping.student_id == Student.student_id)
            .join(SchoolStreamClass, SchoolStreamClass.class_id == SchoolClassStudentMapping.class_id)
            .join(SchoolStream, SchoolStream.school_stream_id == SchoolStreamClass.school_stream_id)
            .where(Student.student_id == student_id, SchoolClassStudentMapping.is_active == 1)
        )
        result = await db.execute(stmt)
        row = result.first()

        if row:
            s         = row[0]
            class_id  = row.class_id
            school_id = s.school_id if hasattr(s, "school_id") else None
            profile = {
                "student_id":  s.student_id,
                "name":        f"{s.first_name} {s.last_name or ''}".strip(),
                "phone":       s.phone,
                "class":       f"{row.class_name} - {row.class_code} Section",
                "stream":      row.stream_name,
                "class_id":    class_id,
            }

        if not school_id and class_id:
            sc_result = await db.execute(select(SchoolStreamClass).where(SchoolStreamClass.class_id == class_id))
            sc = sc_result.scalar_one_or_none()
            if sc:
                school_id = sc.school_id

        banners = []
        if school_id:
            banner_rows = (await db.execute(select(SchoolBanner).where(
                SchoolBanner.school_id == school_id, SchoolBanner.status == 1)
                .order_by(SchoolBanner.created_at.desc()))).scalars().all()
            banners = [{"id": b.id, "bannerlink": b.bannerlink} for b in banner_rows]

        events = []
        if school_id:
            event_rows = (await db.execute(select(SchoolEvent).where(
                SchoolEvent.school_id == school_id, SchoolEvent.status == 1)
                .order_by(SchoolEvent.created_at.desc()).limit(3))).scalars().all()
            events = [{"id": e.id, "title": e.title, "description": e.description,
                "created_at": e.created_at.isoformat()} for e in event_rows]

        today_classes = []
        if class_id:
            tt_stmt = (
                select(TimeTable.id, TimeTable.start_time, TimeTable.end_time,
                       TimeTable.duration, TimeTable.day, SchoolStreamSubject.subject_name)
                .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
                .where(TimeTable.class_id == class_id, TimeTable.day == day_name)
                .order_by(TimeTable.start_time)
            )
            tt_rows = (await db.execute(tt_stmt)).all()
            today_classes = [
                {"id": r.id, "subject": r.subject_name or "N/A",
                 "start_time": r.start_time.strftime("%I:%M %p") if r.start_time else None,
                 "end_time": r.end_time.strftime("%I:%M %p") if r.end_time else None,
                 "duration_min": r.duration, "day": r.day}
                for r in tt_rows
            ]

        timetable = []
        if class_id:
            full_tt_stmt = (
                select(TimeTable.id, TimeTable.start_time, TimeTable.end_time,
                       TimeTable.duration, TimeTable.day, SchoolStreamSubject.subject_name)
                .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == TimeTable.subject_id)
                .where(TimeTable.class_id == class_id)
                .order_by(TimeTable.day, TimeTable.start_time)
                .limit(10)
            )
            full_tt_rows = (await db.execute(full_tt_stmt)).all()
            timetable = [
                {"id": r.id, "subject": r.subject_name or "N/A",
                 "start_time": r.start_time.strftime("%I:%M %p") if r.start_time else None,
                 "end_time": r.end_time.strftime("%I:%M %p") if r.end_time else None,
                 "duration_min": r.duration, "day": r.day}
                for r in full_tt_rows
            ]

        online_classes = []
        if school_id and class_id:
            oc_rows = (await db.execute(
                select(OnlineClass, SchoolStreamSubject.subject_name)
                .outerjoin(SchoolStreamSubject, SchoolStreamSubject.subject_id == OnlineClass.subject_id)
                .where(OnlineClass.class_id == class_id, OnlineClass.scheduled_at >= datetime.utcnow())
                .order_by(OnlineClass.scheduled_at.asc()).limit(3)
            )).all()
            online_classes = [
                {"id": r[0].id, "title": r[0].title, "subject": r.subject_name or "N/A",
                 "meeting_link": r[0].meeting_link,
                 "scheduled_at": r[0].scheduled_at.isoformat(),
                 "duration_min": r[0].duration_min}
                for r in oc_rows
            ]

        notices = []
        if school_id:
            notice_rows = (await db.execute(select(SchoolNotice).where(
                SchoolNotice.school_id == school_id, SchoolNotice.status == 1)
                .order_by(SchoolNotice.created_at.desc()).limit(3))).scalars().all()
            notices = [{"id": n.id, "title": n.title, "description": n.description,
                "created_at": n.created_at.isoformat()} for n in notice_rows]

        gallery = []
        if school_id:
            gallery_rows = (await db.execute(select(SchoolGallery).where(
                SchoolGallery.school_id == school_id, SchoolGallery.status == 1)
                .order_by(SchoolGallery.created_at.desc()).limit(6))).scalars().all()
            gallery = [{"id": g.id, "bannerlink": g.bannerlink} for g in gallery_rows]

        dashboard_data = {
            "profile":        profile,
            "banners":        banners,
            "events":         {"data": events,         "has_more": len(events) == 3},
            "today_classes":  {"date": str(today), "day": day_name, "data": today_classes},
            "timetable":      {"data": timetable,      "has_more": len(timetable) == 10},
            "online_classes": {"data": online_classes, "has_more": len(online_classes) == 3},
            "notices":        {"data": notices,        "has_more": len(notices) == 3},
            "gallery":        {"data": gallery,        "has_more": len(gallery) == 6},
        }

        await cache.set(cache_key, dashboard_data, expire=600)

        return ResultResponse(code=200, status="Success",
            message="Student dashboard fetched successfully",
            result={"cache": False, **dashboard_data})

    except HTTPException:
        raise
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")
