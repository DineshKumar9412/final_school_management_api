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
admin_router = APIRouter(tags=["WEB API'S FOR ADMIN"])

@admin_router.post("/admin/school_group", response_model=ResultResponse)
async def create_school_group(
    group: SchoolGroupCreate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolGroup).where(
        SchoolGroup.school_id == group.school_id,
        SchoolGroup.group_name == group.group_name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return ResultResponse(
            code=409,
            message="School Group already exists"
        )

    new_group = SchoolGroup(**group.model_dump())
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)

    return ResultResponse(
        code=200,
        status="Success",
        message="School group created successfully",
        result={
            "id": new_group.school_group_id,
            "name": new_group.group_name
        }
    )

@admin_router.put("/school_group/{group_id}", response_model=ResultResponse)
async def update_school_group(
    group_id: int,
    group: SchoolGroupCreate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
    result = await db.execute(stmt)
    school_group = result.scalar_one_or_none()

    if not school_group:
        return ResultResponse(
            code=404,
            message="Group not found"
        )

    school_group.group_name = group.group_name

    await db.commit()
    await db.refresh(school_group)

    return ResultResponse(
        code=200,
        status="Success",
        message="Group updated successfully"
    )

@admin_router.delete("/school_group/{group_id}", response_model=ResultResponse)
async def delete_school_group(
    group_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolGroup).where(SchoolGroup.school_group_id == group_id)
    result = await db.execute(stmt)
    school_group = result.scalar_one_or_none()

    if not school_group:
        return ResultResponse(
            code=404,
            message="Group not found"
        )

    await db.delete(school_group)
    await db.commit()

    return ResultResponse(
        code=200,
        status="Success",
        message="Group deleted successfully"
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
    
    data = [{"id": g.school_group_id, "name": g.group_name} for g in groups]    
    return ResultResponse(
        code=200,
        status = "Success",
        message="School groups fetched successfully",
        result = {
            "data" : data
        }
    )

@admin_router.post("/admin/school_stream", response_model=ResultResponse)
async def create_school_stream(
    schoolstream: SchoolStreamCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if stream already exists for the school
    stmt = select(SchoolStream).where(
        SchoolStream.school_id == schoolstream.school_id,
        SchoolStream.stream_name == schoolstream.stream_name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return ResultResponse(
            code=409,
            status="Failed",
            message="School Stream already exists",
            result={
                "stream": existing.stream_name,
                "status": existing.status
            }
        )

    stream_obj = SchoolStream(**schoolstream.model_dump())
    db.add(stream_obj)
    await db.commit()
    await db.refresh(stream_obj)

    return ResultResponse(
        code=200,
        status="Success",
        message="School Stream created successfully",
        result={
            "id": stream_obj.school_stream_id,
            "stream": stream_obj.stream_name,
            "status": stream_obj.status
        }
    )

@admin_router.put("/admin/school_stream/{stream_id}", response_model=ResultResponse)
async def update_school_stream(
    stream_id: int,
    schoolstream: SchoolStreamCreate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolStream).where(SchoolStream.school_stream_id == stream_id)
    result = await db.execute(stmt)
    stream_obj = result.scalar_one_or_none()

    if not stream_obj:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Stream not found"
        )

    # Update fields
    stream_obj.stream_name = schoolstream.stream_name
    stream_obj.stream_code = schoolstream.stream_code
    stream_obj.status = schoolstream.status

    await db.commit()
    await db.refresh(stream_obj)

    return ResultResponse(
        code=200,
        status="Success",
        message="Stream updated successfully",
        result={
            "id": stream_obj.school_stream_id,
            "stream": stream_obj.stream_name,
            "status": stream_obj.status
        }
    )

@admin_router.delete("/admin/school_stream/{stream_id}", response_model=ResultResponse)
async def delete_school_stream(
    stream_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolStream).where(SchoolStream.school_stream_id == stream_id)
    result = await db.execute(stmt)
    stream_obj = result.scalar_one_or_none()

    if not stream_obj:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Stream not found"
        )

    await db.delete(stream_obj)
    await db.commit()

    return ResultResponse(
        code=200,
        status="Success",
        message="Stream deleted successfully",
        result={
            "id": stream_obj.school_stream_id
        }
    )

@admin_router.get("/admin/get_school_stream_list", response_model=ResultResponse)
async def get_school_stream(
    school_id: int,
    db: AsyncSession = Depends(get_db),
):
    # Fetch streams for the given school
    stmt = select(SchoolStream).where(SchoolStream.school_id == school_id)
    result = await db.execute(stmt)
    streams = result.scalars().all()

    # Fetch groups for the given school
    stmt = select(SchoolGroup).where(SchoolGroup.school_id == school_id)
    result = await db.execute(stmt)
    groups = result.scalars().all()

    # Prepare group dropdown data
    group_data = [{"id": g.school_group_id, "name": g.group_name} for g in groups]

    # If no streams found
    if not streams:
        return ResultResponse(
            code=404,
            status="Failed",
            message="No streams found for this school",
            result={
                "group_dropdown": group_data
            }
        )
    # Prepare stream data
    data = [
        {
            "id": s.school_stream_id,
            "stream_name": s.stream_name,
            "stream_code": s.stream_code,

        }
        for s in streams
    ]

    return ResultResponse(
        code=200,
        status="Success",
        message="School streams fetched successfully",
        result={
            "data": data,
            "group_dropdown": group_data
        }
    )


