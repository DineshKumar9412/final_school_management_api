from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from models.common_models import Notification
from schemas.common_schemas import NotificationCreate
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
