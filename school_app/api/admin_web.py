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
from models.admin_models import School, SchoolGroup, SchoolStream, SchoolStreamClass, SchoolStreamSubject, SchoolUser
from database.redis_cache import cache


## ADMIN PAGE ROUTER
admin_router = APIRouter(tags=["WEB API'S FOR ADMIN"])


# ADMIN GROUP

@admin_router.post("/school_group", response_model=ResultResponse)
async def create_school_group(
    group: SchoolGroupCreate,
    db: AsyncSession = Depends(get_db)
):
    
    ### NEED TO CONFIRM WITH NEELA
    stmt = select(SchoolGroup).where(
        SchoolGroup.school_id == group.school_id,
        SchoolGroup.group_name == group.group_name
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return ResultResponse(
            code=409,
            message="School Group already exists",
            result = {}
        )

    ### INSERT NEW GROUP
    new_group = SchoolGroup(**group.model_dump())
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
        
    await cache.delete(f"school:{group.school_id}:group:meta")
    await cache.delete(f"school:{group.school_id}:stream:class:group:subject:all")

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
            message="Group not found",
            result = {}
        )

    school_group.group_name = group.group_name

    await db.commit()
    await db.refresh(school_group)

    await cache.delete(f"school:{group.school_id}:group:meta")
    await cache.delete(f"school:{group.school_id}:stream:class:group:subject:all")
    
    return ResultResponse(
        code=200,
        status="Success",
        message="Group updated successfully",
        result = {}
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
            status="Failed",
            message="Group not found",
            result = {}
        )

    await db.delete(school_group)
    await db.commit()
    
    cache_key = f"school:{school_group.school_id}:group:meta"
    await cache.delete(cache_key)
    
    await cache.delete(f"school:{school_group.school_id}:group:meta")
    await cache.delete(f"school:{school_group.school_id}:stream:class:group:subject:all")
    
    return ResultResponse(
        code=200,
        status="Success",
        message="Group deleted successfully",
        result = {}
    )

@admin_router.get("/get_school_group_list", response_model=ResultResponse,status_code=201)
async def get_school_groups(
    school_id: int,
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"school:{school_id}:group:meta"
    res_cached = await cache.get(cache_key)
    if res_cached:
        return ResultResponse(
        code=200,
        status = "Success",
        message="School groups fetched successfully (cache)",
        result = {
            "cache":"True",
            "data" : res_cached
        }
    )

    stmt = select(SchoolGroup).where(SchoolGroup.school_id == school_id)
    result = await db.execute(stmt)
    groups = result.scalars().all()

    if not groups:
        return ResultResponse(
            code=404,
            status="Failed",
            message="No groups found for this school",
            result= {}
        )
        
    data = [{"id": g.school_group_id, "name": g.group_name} for g in groups] 
    
    await cache.set(cache_key, value=data, expire=600)
    
    return ResultResponse(
        code=200,
        status = "Success",
        message="School groups fetched successfully",
        result = {
            "data" : data
        }
    )


# ADMIN STREAM
@admin_router.post("/school_stream", response_model=ResultResponse)
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

@admin_router.put("/school_stream/{stream_id}", response_model=ResultResponse)
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

@admin_router.delete("/school_stream/{stream_id}", response_model=ResultResponse)
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

@admin_router.get("/get_school_stream_list", response_model=ResultResponse)
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


# ADMIN STREAM CLASS
@admin_router.post("/school_stream_class", response_model=ResultResponse)
async def create_school_stream_class(
    schoolstreamclass: SchoolStreamClassCreate,
    db: AsyncSession = Depends(get_db)
):
    # Check if class already exists in the same stream
    stmt = select(SchoolStreamClass).where(
        SchoolStreamClass.school_id == schoolstreamclass.school_id,
        SchoolStreamClass.school_stream_id == schoolstreamclass.school_stream_id,
        SchoolStreamClass.class_code == schoolstreamclass.class_code
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        return ResultResponse(
            code=409,
            status="Failed",
            message="Class already exists",
            result={
                "class_name": existing.class_name,
                "status": existing.status
            }
        )

    new_class = SchoolStreamClass(**schoolstreamclass.model_dump())
    db.add(new_class)
    await db.commit()
    await db.refresh(new_class)

    return ResultResponse(
        code=200,
        status="Success",
        message="Class created successfully",
        result={
            "id": new_class.class_id,
            "class_name": new_class.class_name,
            "status": new_class.status
        }
    )

@admin_router.put("/school_stream_class/{class_id}", response_model=ResultResponse)
async def update_school_stream_class(
    class_id: int,
    schoolstreamclass: SchoolStreamClassCreate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolStreamClass).where(SchoolStreamClass.class_id == class_id)
    result = await db.execute(stmt)
    stream_class = result.scalar_one_or_none()

    if not stream_class:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Class not found"
        )

    # Update fields
    stream_class.class_name = schoolstreamclass.class_name
    stream_class.class_code = schoolstreamclass.class_code
    stream_class.status = schoolstreamclass.status

    await db.commit()
    await db.refresh(stream_class)

    return ResultResponse(
        code=200,
        status="Success",
        message="Class updated successfully",
        result={
            "id": stream_class.class_id,
            "class_name": stream_class.class_name,
            "status": stream_class.status
        }
    )

@admin_router.delete("/school_stream_class/{class_id}", response_model=ResultResponse)
async def delete_school_stream_class(
    class_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolStreamClass).where(SchoolStreamClass.class_id == class_id)
    result = await db.execute(stmt)
    stream_class = result.scalar_one_or_none()

    if not stream_class:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Class not found",
            result = {}
        )

    await db.delete(stream_class)
    await db.commit()

    return ResultResponse(
        code=200,
        status="Success",
        message="Class deleted successfully",
        result={
            "id": stream_class.class_id
        }
    )

@admin_router.get("/get_school_stream_class_list", response_model=ResultResponse)
async def get_school_stream(
    school_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SchoolStreamClass).where(SchoolStreamClass.school_id == school_id)
    result = await db.execute(stmt)
    stream_class = result.scalars().all()

    gr_str_stmt = (
        select(
            SchoolGroup.school_group_id,
            SchoolGroup.group_name,
            SchoolStream.school_stream_id,
            SchoolStream.stream_name
        )
        .outerjoin(
            SchoolStream,
            SchoolGroup.school_group_id == SchoolStream.school_group_id
        )
        .where(SchoolGroup.school_id == school_id)
    )

    gr_str_result = await db.execute(gr_str_stmt)
    gr_str_res = gr_str_result.all()

    ### GROUP AND STREAM
    group_list = {}
    stream_list = {}
    for school_id, group_name, stream_id, stream_name in gr_str_res:
        group_list[school_id] = group_name
        stream_list.setdefault(school_id, {})[stream_id] = stream_name

    if not stream_class:
        return ResultResponse(
            code=404,
            status="Failed",
            message="No stream found for this school",
            result = {
                "group_dropdown": group_list,
                "stream_dropdown" : stream_list
            }
        )
    
    data = [
        {
            "id":streamclass.class_id,
            "school_stream_id": streamclass.school_stream_id,
            "class_name": streamclass.class_name,
            "class_code":streamclass.class_code
        }
        for streamclass in stream_class
    ]

    return ResultResponse(
        code=200,
        status = "Success",
        message="School streamclass fetched successfully",
        result = {
            "group_dropdown": group_list,
            "stream_dropdown" : stream_list,
            "data" : data
        }
    )


# ADMIN STREAM SUBJECTS
@admin_router.post("/school_stream_subject",response_model=ResultResponse,status_code=201)
async def create_school_stream_subject(
    payload: SchoolStreamSubjectCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if subject already exists for the stream
        stmt = select(SchoolStreamSubject).where(
            SchoolStreamSubject.school_stream_id == payload.school_stream_id,
            SchoolStreamSubject.subject_name == payload.subject_name
        )
        result = await db.execute(stmt)
        existing_subject = result.scalar_one_or_none()

        if existing_subject:            
            return ResultResponse(
                code=409,
                status="Failed",
                message="Subject already exists for this stream"
            )
        
        new_subject = SchoolStreamSubject(
            **payload.model_dump(exclude_unset=True)
        )

        db.add(new_subject)
        await db.commit()
        await db.refresh(new_subject)

        return ResultResponse(
            code=201,
            message="Class created successfully",
            status = "Success",
            result={
                "id": new_subject.subject_id,
                "subject_name": new_subject.subject_name,
                "status": new_subject.status
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message="Internal Server Error",
            resut={
                "error":str(e)}
            )

@admin_router.put("/school_stream_subject/{subject_id}", response_model=ResultResponse,status_code=200)
async def update_school_stream_class(
    subject_id: int,
    schoolstreamclass: SchoolStreamSubjectCreate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolStreamSubject).where(SchoolStreamSubject.subject_id == subject_id)
    result = await db.execute(stmt)
    stream_class = result.scalar_one_or_none()

    if not stream_class:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Class not found"
        )

    # Update fields
    stream_class.class_name = schoolstreamclass.class_name
    stream_class.class_code = schoolstreamclass.class_code
    stream_class.status = schoolstreamclass.status

    await db.commit()
    await db.refresh(stream_class)

    return ResultResponse(
        code=200,
        status="Success",
        message="Class updated successfully",
        result={
            "id": stream_class.class_id,
            "class_name": stream_class.class_name,
            "status": stream_class.status
        }
    )

@admin_router.delete("/school_stream_subject/{subject_id}", response_model=ResultResponse)
async def delete_school_stream_class(
    subject_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolStreamSubject).where(SchoolStreamSubject.subject_id == subject_id)
    result = await db.execute(stmt)
    stream_class = result.scalar_one_or_none()

    if not stream_class:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Class not found",
            result = {}
        )

    await db.delete(stream_class)
    await db.commit()

    return ResultResponse(
        code=200,
        status="Success",
        message="Class deleted successfully",
        result={
            "id": stream_class.class_id
        }
    )

@admin_router.get("/school_stream_subject", response_model=ResultResponse,status_code=200)
async def get_stream_group_classes(
    school_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SchoolStreamClass).where(SchoolStreamClass.school_id == school_id)
    result = await db.execute(stmt)
    stream_class = result.scalars().all()

    gr_str_stmt = (
        select(
            SchoolGroup.school_group_id,
            SchoolGroup.group_name,
            SchoolStream.school_stream_id,
            SchoolStream.stream_name,
            SchoolStreamClass.class_id,
            SchoolStreamClass.class_name
        )
        .outerjoin(
            SchoolStream,
            SchoolGroup.school_group_id == SchoolStream.school_group_id
        )
        .where(SchoolGroup.school_id == school_id)
    )

    gr_str_result = await db.execute(gr_str_stmt)
    gr_str_res = gr_str_result.all()

    group_list = {}
    stream_list = {}
    stream_class = {}
    for school_id, group_name, stream_id, stream_name ,class_id ,class_name in gr_str_res:
        group_list[school_id] = group_name
        stream_list.setdefault(school_id, {})[stream_id] = stream_name
        stream_class.setdefault(school_id, {})[class_id] = class_name
    
    return ResultResponse(
        code=200,
        status = "Success",
        message="No stream found for this school",
        result = {
            "group_dropdown": group_list,
            "stream_dropdown" : stream_list,
            "class_dropdown" : stream_class
        }
    )
    
