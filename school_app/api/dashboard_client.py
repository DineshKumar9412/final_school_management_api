from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
from dateutil.relativedelta import relativedelta
import uuid, time

from database.session import get_db
from schemas.user_schemas import DeviceRegisterRequest
from schemas.admin_schemas import ResultResponse
from models.user_models import DeviceRegistration, Session as SessionModel, FcmToken
from helper.decorators import validate_session
from helper.optmessage import _send_otp_logic, _verify_otp_logic
from schemas.user_schemas import SignIN,ChooseAccountRequest
from database.redis_cache import cache
from models.student_web_models import Student
from models.admin_models import SchoolUser


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
        # ── Fetch existing session ────────────────────────────────────
        stmt = select(SessionModel).where(
            SessionModel.device_id == device.id
        )
        result = await db.execute(stmt)
        session_data = result.scalar_one_or_none()

        return ResultResponse(
            code=202,
            status="Success",
            message="Device already registered.",
            result={
                "client_key": session_data.client_key if session_data else None
            }
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

    # ── 3. Insert FCM token ───────────────────────────────────────────
    fcm = FcmToken(
        fcm_token = payload.fcm_token,
    )
    db.add(fcm)

    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device registration conflict."
        )

    # ── 4. Generate client_key from device_id (UUID v5) ───────────────
    client_key = str(uuid.uuid5(uuid.NAMESPACE_DNS, payload.device_id + str(time.time())))

    # ── 5. Create session valid for 3 months ─────────────────────────
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
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session creation conflict."
        )

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
    # ── 1. Generate new client_key and extend valid_till ──────────────
    new_client_key = str(uuid.uuid4())
    new_valid_till = datetime.utcnow() + relativedelta(months=3)

    # ── 2. Update session in DB ───────────────────────────────────────
    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()

    if not session_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found."
        )

    session_db.client_key = new_client_key
    session_db.valid_till = new_valid_till

    try:
        await db.commit()
        await db.refresh(session_db)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Session refresh conflict."
        )

    # ── 3. Invalidate old cache key ───────────────────────────────────
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

# ── Helper: find all matching accounts by phone ───────────────────────
async def _get_accounts_by_phone(identifier: str, db: AsyncSession) -> list[dict]:
    accounts = []

    stmt = select(Student).where(Student.phone == identifier)
    result = await db.execute(stmt)
    students = result.scalars().all()
    for s in students:
        accounts.append({
            "inq_id": s.student_inq_id,
            "role":   "student",
            "name":   s.name if hasattr(s, "name") else None,
        })

    stmt = select(SchoolUser).where(SchoolUser.phone == identifier)
    result = await db.execute(stmt)
    users = result.scalars().all()
    for u in users:
        accounts.append({
            "inq_id": u.user_inq_id,
            "role":   "teacher",
            "name":   u.name if hasattr(u, "name") else None,
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

    # ── Send OTP ──────────────────────────────────────────────────────
    if not otp and not resend:
        await _send_otp_logic(identifier=identifier, db=db, fcb_token=fcm_token, opt=otp)
        return ResultResponse(
            code=200, status="Success",
            message="OTP sent successfully.",
            result={"identifier": identifier}
        )

    # ── Resend OTP ────────────────────────────────────────────────────
    if resend:
        await _send_otp_logic(identifier=identifier, db=db, fcb_token=fcm_token, opt=otp)
        return ResultResponse(
            code=200, status="Success",
            message="OTP resent successfully.",
            result={"identifier": identifier}
        )

    # ── Verify OTP ────────────────────────────────────────────────────
    await _verify_otp_logic(identifier=identifier, otp=otp, db=db)

    # ── Check accounts linked to this phone ───────────────────────────
    accounts = await _get_accounts_by_phone(identifier, db)

    if not accounts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found for this phone number."
        )

    # ── Multiple accounts — return list for customer to choose ────────
    if len(accounts) > 1:
        return ResultResponse(
            code=300, status="Choose",
            message="Multiple accounts found. Please choose one.",
            result={"accounts": accounts}
        )

    # ── Single account — auto save session.user_id ────────────────────
    chosen_inq_id = accounts[0]["inq_id"]

    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = str(chosen_inq_id)
        await db.commit()

    return ResultResponse(
        code=200, status="Success",
        message="Login successful.",
        result={
            "inq_id":    chosen_inq_id,
            "role":      accounts[0]["role"],
            "fcm_token": fcm_token,
        }
    )

@dashboard_routers.post("/signin/choose", response_model=ResultResponse)
async def choose_account(
    payload: ChooseAccountRequest,
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    chosen_inq_id = payload.inq_id
    role          = payload.role

    # ── Validate chosen inq_id exists ─────────────────────────────────
    if role == "student":
        stmt = select(Student).where(Student.student_inq_id == chosen_inq_id)
    elif role == "teacher":
        stmt = select(SchoolUser).where(SchoolUser.user_inq_id == chosen_inq_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Must be 'student' or 'teacher'."
        )

    result = await db.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found."
        )

    # ── Save chosen inq_id to session.user_id ─────────────────────────
    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()
    if session_db:
        session_db.user_id = str(chosen_inq_id)
        await db.commit()

    return ResultResponse(
        code=200, status="Success",
        message="Account selected. Login successful.",
        result={
            "inq_id": chosen_inq_id,
            "role":   role,
        }
    )

@dashboard_routers.get("/profile", response_model=ResultResponse)
async def get_profile(
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    user_id = session.user_id

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No account linked to this session. Please sign in first."
        )

    # ── Check Student table ───────────────────────────────────────────
    stmt = select(Student).where(Student.student_inq_id == int(user_id))
    result = await db.execute(stmt)
    student = result.scalar_one_or_none()

    if student:
        return ResultResponse(
            code=200, status="Success",
            message="Profile fetched successfully.",
            result={
                "role":       "student",
                "inq_id":     student.student_inq_id,
                "name":       student.name,
                "phone":      student.phone
            }
        )

    # ── Check SchoolUser (teacher) table ──────────────────────────────
    stmt = select(SchoolUser).where(SchoolUser.user_inq_id == int(user_id))
    result = await db.execute(stmt)
    teacher = result.scalar_one_or_none()

    if teacher:
        return ResultResponse(
            code=200, status="Success",
            message="Profile fetched successfully.",
            result={
                "role":       "teacher",
                "inq_id":     teacher.user_inq_id,
                "name":       teacher.name,
                "phone":      teacher.phone
            }
        )

    # ── No profile found ──────────────────────────────────────────────
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Profile not found."
    )

@dashboard_routers.post("/logout", response_model=ResultResponse)
async def logout(
    session: SessionModel = Depends(validate_session),
    db: AsyncSession = Depends(get_db),
):
    # ── 1. Clear user_id from session in DB ───────────────────────────
    stmt = select(SessionModel).where(SessionModel.id == session.id)
    result = await db.execute(stmt)
    session_db = result.scalar_one_or_none()

    if session_db:
        session_db.user_id = None
        await db.commit()

    # ── 2. Invalidate cache ───────────────────────────────────────────
    cache_key = f"session:{session.client_key}"
    await cache.delete(cache_key)

    return ResultResponse(
        code=200,
        status="Success",
        message="Logged out successfully.",
        result={}
    )