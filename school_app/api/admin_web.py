from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db

from fastapi import Request, Query
from typing import Optional
from sqlalchemy import select, or_, tuple_
from typing import List

from schemas.admin_schemas import ResultResponse, SchoolGroupCreate, SchoolStreamClassCreate,SchoolStreamCreate,SchoolStreamSubjectCreate
from models.admin_models import School, SchoolGroup, SchoolStream,SchoolStreamClass, SchoolStreamSubject,SchoolUser


## ADMIN PAGE ROUTER
admin_router = APIRouter(tags=["WEB PAGE API"])

@admin_router.post("/school_group", response_model=ResultResponse, status_code=200)   
async def school_group(group: SchoolGroupCreate, action: str = Query(...),update_id: Optional[int] = Query(None),db: AsyncSession = Depends(get_db)):
    try:
        if action.lower() == "update_group":
            if not update_id :
                raise HTTPException(
                status_code=400,
                detail="update_id is required when action=update_group"
            )
                
            stmt = select(SchoolGroup).where(SchoolGroup.school_group_id == update_id)
            result = await db.execute(stmt)
            school_group = result.scalar_one_or_none()
            
            if not school_group:
                return ResultResponse(
                    code=404,
                    status="Failed",
                    message="No groups found for this school"
                )
                
            school_group.group_name = group.group_name
            await db.commit()
            await db.refresh(school_group)

            return ResultResponse(
                code=200,
                status = "Success",
                message="Group name updated successfully",
                result = {
                    "id": school_group.school_group_id,
                    "name": school_group.group_name
                }
            )
            
        elif action.lower() == "create_group":
            stmt = select(SchoolGroup).where(
                SchoolGroup.school_id == group.school_id,
                SchoolGroup.group_name == group.group_name,
            )
            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return ResultResponse(
                code=409,
                message="School Group already exist",
                result = {
                    "group":existing.group_name,
                    "status":existing.status})

            new_group = SchoolGroup(**group.model_dump())

            db.add(new_group)
            await db.commit()
            await db.refresh(new_group)
            return ResultResponse(
                code=200,
                status = "Success",
                message="School group created successfully",
                result={
                    "group":new_group.group_name,
                    "status":new_group.status
                }
            )
        
        elif action.lower() == "delete_group":
            if not update_id:
                raise HTTPException(
                    status_code=400,
                    detail="update_id is required when action=delete_group"
                )
            stmt = select(SchoolGroup).where(SchoolGroup.school_group_id == update_id)
            result = await db.execute(stmt)
            school_group = result.scalar_one_or_none()

            if not school_group:
                return ResultResponse(
                    code=404,
                    message="No groups found for this school"
                )

            await db.delete(school_group)
            await db.commit()

            return ResultResponse(
                code=200,
                status = "Success",
                message="Group deleted successfully",
                result={
                    "id": school_group.school_group_id
                }
            )
        
        else:
            return ResultResponse(
                code=400,
                message="Invalid action"
            )
            
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Database constraint violation {}".format(str(e))
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@admin_router.get("/get_school_group_list", response_model=ResultResponse)
async def get_school_groups(
    school_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SchoolGroup).where(SchoolGroup.school_id == school_id)
    result = await db.execute(stmt)
    groups = result.scalars().all()
    if not groups:
        return ResultResponse(
            code=404,
            message="No groups found for this school"
        )
        
    data = []
    for group in groups:
        data.append({
            "id": group.school_group_id,
            "name": group.group_name
        })

    return ResultResponse(
        code=200,
        status = "Success",
        message="School groups fetched successfully",
        result = {
            "data" : data
        }
    )
