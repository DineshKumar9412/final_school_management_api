# notice_web.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.redis_cache import cache
from models.notice_models import SchoolNotice
from schemas.notice_schemas import SchoolNoticeCreate, SchoolNoticeUpdate
from schemas.admin_schemas import ResultResponse


# ── Web Routes (Admin/School team) ────────────────────────────────────────────
notice_web_router = APIRouter(tags=["WEB API'S NOTICE"])

# ── Client Routes (Android/iOS team) ──────────────────────────────────────────
notice_client_router = APIRouter(tags=["CLIENT API'S DASHBOARD"])


def _cache_key(school_id: int) -> str:
    return f"school:{school_id}:notice"


# ─────────────────────────────────────────────────────────────────────────────
# WEB — POST /notice
# ─────────────────────────────────────────────────────────────────────────────
@notice_web_router.post("/notice", response_model=ResultResponse)
async def create_notice(
    payload: SchoolNoticeCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_notice = SchoolNotice(
            school_id   = payload.school_id,
            title       = payload.title,
            description = payload.description,
            status      = payload.status if payload.status is not None else 1,
        )
        db.add(new_notice)
        await db.commit()
        await db.refresh(new_notice)

        await cache.delete(_cache_key(payload.school_id))

        return ResultResponse(
            code=201,
            status="Success",
            message="Notice created successfully",
            result={
                "id":          new_notice.id,
                "school_id":   new_notice.school_id,
                "title":       new_notice.title,
                "description": new_notice.description,
                "status":      new_notice.status,
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# WEB — PUT /notice/{id}
# ─────────────────────────────────────────────────────────────────────────────
@notice_web_router.put("/notice/{notice_id}", response_model=ResultResponse)
async def update_notice(
    notice_id: int,
    payload: SchoolNoticeUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolNotice).where(SchoolNotice.id == notice_id)
        result = await db.execute(stmt)
        notice = result.scalar_one_or_none()

        if not notice:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Notice not found",
                result={}
            )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(notice, key, value)

        await db.commit()
        await db.refresh(notice)

        await cache.delete(_cache_key(notice.school_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Notice updated successfully",
            result={
                "id":          notice.id,
                "school_id":   notice.school_id,
                "title":       notice.title,
                "description": notice.description,
                "status":      notice.status,
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# WEB — DELETE /notice/{id}  → soft delete (status = 0)
# ─────────────────────────────────────────────────────────────────────────────
@notice_web_router.delete("/notice/{notice_id}", response_model=ResultResponse)
async def delete_notice(
    notice_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolNotice).where(SchoolNotice.id == notice_id)
        result = await db.execute(stmt)
        notice = result.scalar_one_or_none()

        if not notice:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Notice not found",
                result={}
            )

        notice.status = 0  # soft delete
        await db.commit()

        await cache.delete(_cache_key(notice.school_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Notice deleted successfully",
            result={"id": notice_id}
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT — GET /notice?school_id=   (only active notices)
# ─────────────────────────────────────────────────────────────────────────────
@notice_client_router.get("/notice", response_model=ResultResponse)
async def get_notices(
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
                message="Notices fetched successfully (cache)",
                result={"cache": True, "data": cached}
            )

        stmt = select(SchoolNotice).where(
            SchoolNotice.school_id == school_id,
            SchoolNotice.status == 1
        ).order_by(SchoolNotice.created_at.desc())

        result = await db.execute(stmt)
        notices = result.scalars().all()

        if not notices:
            return ResultResponse(
                code=404,
                status="Failed",
                message="No notices found",
                result={}
            )

        data = [
            {
                "id":          n.id,
                "title":       n.title,
                "description": n.description,
                "created_at":  n.created_at.isoformat(),
            }
            for n in notices
        ]

        await cache.set(ck, data, expire=600)

        return ResultResponse(
            code=200,
            status="Success",
            message="Notices fetched successfully",
            result={"cache": False, "data": data}
        )

    except Exception as e:
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )
