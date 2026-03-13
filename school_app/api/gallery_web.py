# gallery_web.py — WEB (POST/PUT/DELETE/GET)
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.redis_cache import cache
from models.gallery_models import SchoolGallery
from schemas.gallery_schemas import SchoolGalleryCreate, SchoolGalleryUpdate
from schemas.admin_schemas import ResultResponse

gallery_web_router = APIRouter(tags=["WEB API'S GALLERY"])


def _cache_key(school_id: int) -> str:
    return f"school:{school_id}:gallery"


@gallery_web_router.post("/gallery", response_model=ResultResponse)
async def create_gallery(payload: SchoolGalleryCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_item = SchoolGallery(school_id=payload.school_id, bannerlink=payload.bannerlink,
            status=payload.status if payload.status is not None else 1)
        db.add(new_item)
        await db.commit()
        await db.refresh(new_item)
        await cache.delete(_cache_key(payload.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=201, status="Success", message="Gallery created successfully",
            result={"id": new_item.id, "school_id": new_item.school_id,
                    "bannerlink": new_item.bannerlink, "status": new_item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


@gallery_web_router.put("/gallery/{gallery_id}", response_model=ResultResponse)
async def update_gallery(gallery_id: int, payload: SchoolGalleryUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolGallery).where(SchoolGallery.id == gallery_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Gallery not found", result={})
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(item, key, value)
        await db.commit()
        await db.refresh(item)
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Gallery updated successfully",
            result={"id": item.id, "school_id": item.school_id,
                    "bannerlink": item.bannerlink, "status": item.status})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


@gallery_web_router.delete("/gallery/{gallery_id}", response_model=ResultResponse)
async def delete_gallery(gallery_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(SchoolGallery).where(SchoolGallery.id == gallery_id))
        item = result.scalar_one_or_none()
        if not item:
            return ResultResponse(code=404, status="Failed", message="Gallery not found", result={})
        item.status = 0
        await db.commit()
        await cache.delete(_cache_key(item.school_id))
        await cache.delete_pattern("student:*:dashboard")
        return ResultResponse(code=200, status="Success", message="Gallery deleted successfully", result={"id": gallery_id})
    except Exception as e:
        await db.rollback()
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# WEB — GET /gallery?school_id=   (all records including inactive)
# ─────────────────────────────────────────────────────────────────────────────
@gallery_web_router.get("/gallery", response_model=ResultResponse)
async def get_gallery(
    school_id: int = Query(..., description="School ID"),
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolGallery).where(
            SchoolGallery.school_id == school_id
        ).order_by(SchoolGallery.created_at.desc())
        result = await db.execute(stmt)
        items = result.scalars().all()

        if not items:
            return ResultResponse(code=404, status="Failed", message="No gallery found", result={})

        data = [{"id": i.id, "bannerlink": i.bannerlink, "status": i.status,
                 "created_at": i.created_at.isoformat()} for i in items]

        return ResultResponse(code=200, status="Success", message="Gallery fetched successfully",
            result={"total": len(data), "data": data})
    except Exception as e:
        return ResultResponse(code=500, status="Failed", message=f"Internal server error: {str(e)}")
