# gallery_web.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.session import get_db
from database.redis_cache import cache
from models.gallery_models import SchoolGallery
from schemas.gallery_schemas import SchoolGalleryCreate, SchoolGalleryUpdate
from schemas.admin_schemas import ResultResponse


# ── Web Routes (Admin/School team) ───────────────────────────────────────────
gallery_web_router = APIRouter(tags=["WEB API'S GALLERY"])

# ── Client Routes (Android/iOS team) ─────────────────────────────────────────
gallery_client_router = APIRouter(tags=["CLIENT API'S DASHBOARD"])


def _cache_key(school_id: int) -> str:
    return f"school:{school_id}:gallery"


# ─────────────────────────────────────────────────────────────────────────────
# WEB — POST  /gallery
# ─────────────────────────────────────────────────────────────────────────────
@gallery_web_router.post("/gallery", response_model=ResultResponse)
async def create_gallery(
    payload: SchoolGalleryCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        new_banner = SchoolGallery(
            school_id=payload.school_id,
            bannerlink=payload.bannerlink,
            status=payload.status if payload.status is not None else 1
        )
        db.add(new_banner)
        await db.commit()
        await db.refresh(new_banner)

        await cache.delete(_cache_key(payload.school_id))

        return ResultResponse(
            code=201,
            status="Success",
            message="Gallery banner created successfully",
            result={
                "id": new_banner.id,
                "school_id": new_banner.school_id,
                "bannerlink": new_banner.bannerlink,
                "status": new_banner.status
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
# WEB — PUT  /gallery/{id}
# ─────────────────────────────────────────────────────────────────────────────
@gallery_web_router.put("/gallery/{gallery_id}", response_model=ResultResponse)
async def update_gallery(
    gallery_id: int,
    payload: SchoolGalleryUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolGallery).where(SchoolGallery.id == gallery_id)
        result = await db.execute(stmt)
        banner = result.scalar_one_or_none()

        if not banner:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Gallery banner not found",
                result={}
            )

        update_data = payload.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(banner, key, value)

        await db.commit()
        await db.refresh(banner)

        await cache.delete(_cache_key(banner.school_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Gallery banner updated successfully",
            result={
                "id": banner.id,
                "school_id": banner.school_id,
                "bannerlink": banner.bannerlink,
                "status": banner.status
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
# WEB — DELETE  /gallery/{id}   → soft delete (status = 0)
# ─────────────────────────────────────────────────────────────────────────────
@gallery_web_router.delete("/gallery/{gallery_id}", response_model=ResultResponse)
async def delete_gallery(
    gallery_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolGallery).where(SchoolGallery.id == gallery_id)
        result = await db.execute(stmt)
        banner = result.scalar_one_or_none()

        if not banner:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Gallery banner not found",
                result={}
            )

        banner.status = 0  # soft delete
        await db.commit()

        await cache.delete(_cache_key(banner.school_id))

        return ResultResponse(
            code=200,
            status="Success",
            message="Gallery banner deleted successfully",
            result={"id": gallery_id}
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLIENT — GET  /gallery?school_id=  (only active banners)
# ─────────────────────────────────────────────────────────────────────────────
@gallery_client_router.get("/gallery", response_model=ResultResponse)
async def get_gallery(
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
                message="Gallery fetched successfully (cache)",
                result={"cache": True, "data": cached}
            )

        stmt = select(SchoolGallery).where(
            SchoolGallery.school_id == school_id,
            SchoolGallery.status == 1
        ).order_by(SchoolGallery.created_at.desc())

        result = await db.execute(stmt)
        banners = result.scalars().all()

        if not banners:
            return ResultResponse(
                code=404,
                status="Failed",
                message="No gallery banners found",
                result={}
            )

        data = [
            {
                "id": b.id,
                "bannerlink": b.bannerlink,
                "created_at": b.created_at.isoformat()
            }
            for b in banners
        ]

        await cache.set(ck, data, expire=600)

        return ResultResponse(
            code=200,
            status="Success",
            message="Gallery fetched successfully",
            result={"cache": False, "data": data}
        )

    except Exception as e:
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )
