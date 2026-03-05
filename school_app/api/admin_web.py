from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db

from fastapi import Request, Query
from typing import Optional
from sqlalchemy import select, or_, tuple_
from typing import List

from schemas.admin_schemas import ResultResponse, SchoolGroupCreate, SchoolStreamClassCreate,SchoolStreamCreate,SchoolStreamSubjectCreate,\
                                    SchoolStreamUpdate,SchoolStreamClassUpdate,SchoolStreamSubjectUpdate
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
            status="Failed",
            message="School Group already exists",
            result = {}
        )

    ### INSERT NEW GROUP
    new_group = SchoolGroup(**group.model_dump())
    db.add(new_group)
    await db.commit()
    await db.refresh(new_group)
        
    await cache.delete(f"school:{group.school_id}:group:meta")

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
            status="Failed",
            message="Group not found",
            result = {}
        )

    school_group.group_name = group.group_name

    await db.commit()
    await db.refresh(school_group)

    await cache.delete(f"school:{group.school_id}:group:meta")
    
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
    
    return ResultResponse(
        code=200,
        status="Success",
        message="Group deleted successfully",
        result = {}
    )

@admin_router.get("/get_school_group_list", response_model=ResultResponse)
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

    await cache.delete(f"school:{schoolstream.school_id}:stream:meta")
    
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
    payload: SchoolStreamUpdate,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(SchoolStream).where(
        SchoolStream.school_stream_id == stream_id
    )

    result = await db.execute(stmt)
    stream_obj = result.scalar_one_or_none()

    if not stream_obj:
        return ResultResponse(
            code=404,
            status="Failed",
            message="Stream not found",
            result={}
        )

    # Only update provided fields
    update_data = payload.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(stream_obj, key, value)

    await db.commit()
    await db.refresh(stream_obj)

    # Invalidate cache
    await cache.delete(f"school:{stream_obj.school_id}:stream:meta")

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
            message="Stream not found",
            result= {}
        )

    await db.delete(stream_obj)
    await db.commit()

    await cache.delete(f"school:{stream_obj.school_id}:stream:meta")
    
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
    
    cache_key = f"school:{school_id}:stream:meta"
    cached_data = await cache.get(cache_key)
    
    if cached_data:
        return ResultResponse(
            code=200,
            status="Success",
            message="School streams fetched successfully (cache)",
            result={
                "cache": True,
                "data": cached_data
            }
        )
    # Fetch streams for the given school
    stmt = select(SchoolStream).where(SchoolStream.school_id == school_id)
    result = await db.execute(stmt)
    streams = result.scalars().all()

    # If no streams found
    if not streams:
        return ResultResponse(
            code=404,
            status="Failed",
            message="No streams found for this school",
            result={}
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

    await cache.set(cache_key, data, expire=86400)
    
    return ResultResponse(
        code=200,
        status="Success",
        message="School streams fetched successfully",
        result={
            "data": data
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

    version_key = f"school:{schoolstreamclass.school_id}:stream_class:version"
    await cache.incr(version_key)
    
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

@admin_router.patch("/school_stream_class/{class_id}/{school_id}", response_model=ResultResponse)
async def update_school_stream_class(
    school_id: int,
    class_id: int,
    payload: SchoolStreamClassUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # -------- Secure Query (Validate School) --------
        stmt = select(SchoolStreamClass).where(
            SchoolStreamClass.class_id == class_id,
            SchoolStreamClass.school_id == school_id
        )

        result = await db.execute(stmt)
        stream_class = result.scalar_one_or_none()

        if not stream_class:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Class not found for this school",
                result={}
            )

        # -------- Partial Update --------
        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(stream_class, key, value)

        await db.commit()
        await db.refresh(stream_class)

        # -------- Version-Based Cache Invalidation --------
        version_key = f"school:{school_id}:stream_class:version"
        await cache.incr(version_key)

        return ResultResponse(
            code=200,
            status="Success",
            message="Class updated successfully",
            result={
                "id": stream_class.class_id,
                "class_name": stream_class.class_name,
                "class_code": stream_class.class_code,
                "status": stream_class.status
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )

@admin_router.delete("/school_stream_class/{class_id}/{school_id}", response_model=ResultResponse)
async def delete_school_stream_class(
    school_id:int,
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

    version_key = f"school:{school_id}:stream_class:version"
    await cache.incr(version_key)
        
    return ResultResponse(
        code=200,
        status="Success",
        message="Class deleted successfully",
        result={
            "id": stream_class.class_id
        }
    )
    
@admin_router.get("/get_school_stream_class_list", response_model=ResultResponse)
async def get_school_stream_class_list(
    school_id: int,
    school_stream_id: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        # -------- Version Key --------
        base_key = f"school:{school_id}:stream_class"
        version_key = f"{base_key}:version"

        version = await cache.get(version_key)
        version = int(version) if version else 0


        if school_stream_id:
            cache_key = f"{base_key}:v{version}:stream_class:{school_stream_id}"
        else:
            cache_key = f"{base_key}:v{version}:stream_class:all"

        cached_data = await cache.get(cache_key)
        if cached_data:
            return ResultResponse(
                code=200,
                status="success",
                message="School stream classes fetched successfully (cache)",
                result={"cache": True, "data": cached_data}
        )

        # -------- DB Query --------
        filters = [SchoolStreamClass.school_id == school_id]

        if school_stream_id:
            filters.append(
                SchoolStreamClass.school_stream_id == school_stream_id
            )

        stmt = select(SchoolStreamClass).where(*filters)

        result = await db.execute(stmt)
        stream_classes = result.scalars().all()

        if not stream_classes:
            return ResultResponse(
                code=404,
                status="failed",
                message="No stream classes found",
                result={}
            )

        data = [
            {
                "id": sc.class_id,
                "school_stream_id": sc.school_stream_id,
                "class_name": sc.class_name,
                "class_code": sc.class_code,
                "status": sc.status
            }
            for sc in stream_classes
        ]

        # -------- Store Cache --------
        await cache.set(cache_key, data, expire=86400)

        return ResultResponse(
            code=200,
            status="success",
            message="School stream classes fetched successfully",
            result={
                "cache": False,
                "data": data
            }
        )

    except Exception as e:
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )    

# ADMIN STREAM SUBJECTS
@admin_router.post("/school_stream_subject",response_model=ResultResponse)
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
                message="Subject already exists for this stream",
                result = {}
            )
        
        new_subject = SchoolStreamSubject(
            **payload.model_dump(exclude_unset=True)
        )

        db.add(new_subject)
        await db.commit()
        await db.refresh(new_subject)
        
        await cache.incr(
            f"stream:{payload.school_stream_id}:subject:version"
        )
        
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

@admin_router.patch("/school_stream_subject/{subject_id}", response_model=ResultResponse)
async def update_school_stream_subject(
    subject_id: int,
    payload: SchoolStreamSubjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolStreamSubject).where(
            SchoolStreamSubject.subject_id == subject_id
        )

        result = await db.execute(stmt)
        subject = result.scalar_one_or_none()

        if not subject:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Subject not found",
                result={}
            )

        # -------- Partial Update --------
        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(subject, key, value)

        await db.commit()
        await db.refresh(subject)

        # -------- Cache Invalidation --------
        await cache.incr(
            f"stream:{subject.school_stream_id}:subject:version"
        )

        return ResultResponse(
            code=200,
            status="Success",
            message="Subject updated successfully",
            result={
                "id": subject.subject_id,
                "subject_name": subject.subject_name,
                "status": subject.status,
                "sort_order": subject.sort_order
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )
        
@admin_router.delete("/school_stream_subject/{subject_id}", response_model=ResultResponse)
async def delete_school_stream_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolStreamSubject).where(
            SchoolStreamSubject.subject_id == subject_id
        )

        result = await db.execute(stmt)
        subject = result.scalar_one_or_none()

        if not subject:
            return ResultResponse(
                code=404,
                status="Failed",
                message="Subject not found",
                result={}
            )

        school_stream_id = subject.school_stream_id

        await db.delete(subject)
        await db.commit()

        # -------- Cache Invalidation --------
        await cache.incr(
            f"stream:{subject.school_stream_id}:subject:version"
        )

        return ResultResponse(
            code=200,
            status="Success",
            message="Subject deleted successfully",
            result={
                "id": subject_id
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )

@admin_router.get("/school_stream_subject", response_model=ResultResponse)
async def get_school_stream_subject(
    school_stream_id: int,
    subject_id: int | None = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        # -------- Version Based Cache --------
        base_key = f"stream:{school_stream_id}:subject"
        version_key = f"{base_key}:version"

        version = await cache.get(version_key)
        version = int(version) if version else 0

        # -------- Cache Key --------
        if subject_id:
            cache_key = f"{base_key}:v{version}:subject:{subject_id}"
        else:
            cache_key = f"{base_key}:v{version}:all"

        # -------- Check Cache --------
        cached_data = await cache.get(cache_key)
        if cached_data:
            return ResultResponse(
                code=200,
                status="Success",
                message="Subjects fetched successfully (cache)",
                result={
                    "cache": True,
                    "data": cached_data
                }
            )

        # -------- DB Query --------
        filters = [
            SchoolStreamSubject.school_stream_id == school_stream_id
        ]

        if subject_id:
            filters.append(
                SchoolStreamSubject.subject_id == subject_id
            )

        stmt = select(SchoolStreamSubject).where(*filters)

        result = await db.execute(stmt)
        subjects = result.scalars().all()

        if not subjects:
            return ResultResponse(
                code=404,
                status="Failed",
                message="No subjects found",
                result={}
            )

        data = [
            {
                "id": sub.subject_id,
                "school_stream_id": sub.school_stream_id,
                "subject_name": sub.subject_name,
                "status": sub.status
            }
            for sub in subjects
        ]

        # -------- Store Cache --------
        await cache.set(cache_key, data, expire=86400)

        return ResultResponse(
            code=200,
            status="Success",
            message="Subjects fetched successfully",
            result={
                "cache": False,
                "data": data
            }
        )

    except Exception as e:
        return ResultResponse(
            code=500,
            status="Failed",
            message=f"Internal server error: {str(e)}"
        )
