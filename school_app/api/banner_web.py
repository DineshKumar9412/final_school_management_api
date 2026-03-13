# banner_web.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from database.session import get_db
from database.redis_cache import cache
from models.banner_models import SchoolBanner
from schemas.banner_schemas import SchoolBannerCreate, SchoolBannerUpdate
from schemas.admin_schemas import ResultResponse

banner_web_router = APIRouter(tags=["WEB API'S BANNER"])

def _cache_key(school_id: int) -> str:
    return f"school:{school_id}:banner"

@banner_web_router.post("/banner", response_model=ResultResponse)
async def create_banner(payload: SchoolBannerCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_item = SchoolBanner(school_id=payload.school_id, bannerlink=payload.bannerlink,
            status=payload.status if payload.status is not None else 1)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        await cache.delete(_cache_key(payload.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=201, status="Success", message="Banner created successfully",
            result={"id": new_item.id, "school_id": new_item.school_id, "bannerlink": new_item.bannerlink, "status": new_item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@banner_web_router.put("/banner/{banner_id}", response_model=ResultResponse)
async def update_banner(banner_id: int, payload: SchoolBannerUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolBanner).where(SchoolBanner.id == banner_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Banner not found", result={})
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await db.commit()
        await db.refresh(item)
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Banner updated successfully",
            result={"id": item.id, "school_id": item.school_id, "bannerlink": item.bannerlink, "status": item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@banner_web_router.delete("/banner/{banner_id}", response_model=ResultResponse)
async def delete_banner(banner_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolBanner).where(SchoolBanner.id == banner_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Banner not found", result={})
        item.status = 0
        await db.commit()
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Banner deleted successfully", result={"id": banner_id})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")

@banner_web_router.get("/banner", response_model=ResultResponse)
async def get_banners(school_id: int = Query(...), db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(SchoolBanner).where(SchoolBanner.school_id == school_id).order_by(SchoolBanner.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()
        if not items:
            return ResultResponse(code=404, status="Failed", message="No banners found", result={})
        data = [{"id": i.id, "bannerlink": i.bannerlink, "status": i.status, "created_at": i.created_at.isoformat()} for i in items]
        return ResultResponse(code=200, status="Success", message="Banners fetched successfully", result={"total": len(data), "data": data})
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")
