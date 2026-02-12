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
admin_router = APIRouter(tags=["WEB PAGE API FOR ADMIN"])

@admin_router.post("/admin/school_group", response_model=ResultResponse, status_code=200)   
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

@admin_router.get("/admin/get_school_group_list", response_model=ResultResponse)
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

@admin_router.post("/admin/school_stream", response_model=ResultResponse, status_code=200)   
async def school_stream(schoolstream: SchoolStreamCreate, action: str = Query(...),update_id: Optional[int] = Query(None) ,db: AsyncSession = Depends(get_db)):
        try:
            # ---------- UPDATE STREAM ----------
            
            if action.lower() == "update_stream":
                if not update_id:
                    return ResultResponse(
                    code=400,
                    message="update_id is required for this action"
                )
                    
                stmt = select(SchoolStream).where(SchoolStream.school_group_id == update_id)
                result = await db.execute(stmt)
                school_stream = result.scalar_one_or_none()
                
                if not school_stream:
                    return ResultResponse(
                        code=404,
                        message="No stream found for this school"
                    )
                    
                school_stream.stream_name = schoolstream.stream_name
                await db.commit()
                await db.refresh(school_stream)

                return ResultResponse(
                    code=200,
                    status = "Success",
                    message="Stream name updated successfully",
                    result = {
                        "id": school_stream.school_stream_id,
                        "name": school_stream.stream_name
                    }
                )
            
            # ---------- CREATE STREAM ----------
            
            elif action.lower() == "create_stream":
                stmt = select(SchoolStream).where(
                    SchoolStream.school_id == schoolstream.school_id,
                    SchoolStream.stream_name == schoolstream.stream_code,
                )
                
                result = await db.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    return ResultResponse(
                    code=409,
                    message="School Stream already exist",
                    status="Failed",
                    result = {
                        "group":existing.stream_name,
                        "status":existing.status})
                    
                stream_obj = SchoolStream(**schoolstream.model_dump())
                db.add(stream_obj)
                await db.commit()
                await db.refresh(stream_obj)
                return ResultResponse(
                    code=200,
                    status = "Success",
                    message="School group created successfully",
                    result={
                        "group":stream_obj.stream_name,
                        "status":stream_obj.status
                    }
                )
            
            elif action.lower() == "delete_stream":
                if not update_id:
                    return ResultResponse(
                        code=400,
                        status="Failed",
                        message="update_id is required for delete_stream"
                    )
                    
                stmt = select(SchoolStream).where(SchoolStream.school_group_id == update_id)
                result = await db.execute(stmt)
                school_stream = result.scalar_one_or_none()

                if not school_stream:
                    return ResultResponse(
                        code=404,
                        message="No stream found for this school"
                    )

                await db.delete(school_stream)
                await db.commit()

                return ResultResponse(
                    code=200,
                    status="Failed",
                    message="Stream deleted successfully",
                    result={
                        "id": school_stream.school_stream_id
                    }
                )
                
            else:
                return ResultResponse(
                    code=400,
                    status="Failed",
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

@admin_router.get("/admin/get_school_stream_list", response_model=ResultResponse)
async def get_school_stream(
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SchoolStream)
    result = await db.execute(stmt)
    groups = result.scalars().all()

    if not groups:
        return ResultResponse(
            code=404,
            status="Failed",
            message="No stream found for this school"
        )
        
    data = []
    for stream in groups:
        data.append({
            "id": stream.school_stream_id,
            "stream_name": stream.stream_name,
            "stream_code":stream.stream_code
        })

    return ResultResponse(
        code=200,
        status = "Success",
        message="School stream fetched successfully",
        result = {
            "data" : data
        }
    )
    
