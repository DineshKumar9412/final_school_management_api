# notice_web.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.redis_cache import cache
from models.notice_models import SchoolNotice
from schemas.notice_schemas import SchoolNoticeCreate, SchoolNoticeUpdate
from schemas.admin_schemas import ResultResponse

notice_web_router = APIRouter(tags=["WEB API'S NOTICE"])

def _cache_key(school_id: int) -> str:
    return f"school:{school_id}:notice"

@notice_web_router.post("/notice", response_model=ResultResponse)
async def create_notice(payload: SchoolNoticeCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_item = SchoolNotice(school_id=payload.school_id, title=payload.title,
            description=payload.description, status=payload.status if payload.status is not None else 1)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        await cache.delete(_cache_key(payload.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=201, status="Success", message="Notice created successfully",
            result={"id": new_item.id, "school_id": new_item.school_id, "title": new_item.title,
                    "description": new_item.description, "status": new_item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@notice_web_router.put("/notice/{notice_id}", response_model=ResultResponse)
async def update_notice(notice_id: int, payload: SchoolNoticeUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolNotice).where(SchoolNotice.id == notice_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Notice not found", result={})
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await db.commit()
        await db.refresh(item)
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Notice updated successfully",
            result={"id": item.id, "school_id": item.school_id, "title": item.title,
                    "description": item.description, "status": item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@notice_web_router.delete("/notice/{notice_id}", response_model=ResultResponse)
async def delete_notice(notice_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolNotice).where(SchoolNotice.id == notice_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Notice not found", result={})
        item.status = 0
        await db.commit()
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Notice deleted successfully", result={"id": notice_id})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@notice_web_router.get("/notice", response_model=ResultResponse)
async def get_notices(school_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(SchoolNotice).where(SchoolNotice.school_id == school_id).order_by(SchoolNotice.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        if not items:
            return ResultResponse(code=404, status="Failed", message="No notices found", result={})
        data = [{"id": i.id, "title": i.title, "description": i.description,
                 "status": i.status, "created_at": i.created_at.isoformat()} for i in items]
        return ResultResponse(code=200, status="Success", message="Notices fetched successfully",
            result={"total": len(data), "data": data})
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")
