from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select,update
from database.session import get_db
from models.student_web_models import StudentInquiry, Student, SchoolClassStudentMapping
from schemas.student_web_schemas import StudentInquiryCreate, StudentCreate, StudentMappingUpdate
from models.admin_models import SchoolStreamClass,SchoolStream
from schemas.admin_schemas import ResultResponse
from fastapi import Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from typing import Optional
from database.redis_cache import cache
import json

import pandas as pd
student_router = APIRouter(tags=["WEB API'S FOR STUDENT"])

cache_ttl = 86400

@student_router.post("/student_admission_inquiries", response_model=ResultResponse)
async def student_admission_inquiries(
    schoolinquiry_payload: StudentInquiryCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        #  Check Duplicate
        stmt = select(StudentInquiry).where(
            StudentInquiry.guardian_phone == schoolinquiry_payload.guardian_phone
        )
        result = await db.execute(stmt)
        existing_inquiry = result.scalars().first()

        if existing_inquiry:
            return ResultResponse(
                code=200,
                status="failed",
                message="Student Inquiry Already Exists",
                result={
                    "student_inq_id": existing_inquiry.student_inq_id,
                    "student_name": existing_inquiry.student_name,
                    "gender": existing_inquiry.gender,
                    "guardian_name": existing_inquiry.guardian_name,
                    "guardian_phone": existing_inquiry.guardian_phone
                }
            )

        #  Create New Inquiry
        new_inquiry = StudentInquiry(
            **schoolinquiry_payload.model_dump(exclude_unset=True)
        )

        db.add(new_inquiry)
        await db.commit()
        await db.refresh(new_inquiry)

        #  Increment Version (Invalidate Cache)
        version_key = f"class:{schoolinquiry_payload.class_id}:student_admission_inquiries:version"
        await cache.incr(version_key)

        return ResultResponse(
            code=201,
            status="Success",
            message="Student inquiry created successfully",
            result={
                "student_inq_id": new_inquiry.student_inq_id,
                "student_name": new_inquiry.student_name,
                "gender": new_inquiry.gender,
                "age": new_inquiry.age,
                "guardian_name": new_inquiry.guardian_name,
                "guardian_phone": new_inquiry.guardian_phone
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )
        
@student_router.get("/get_student_admission_inquiries", response_model=ResultResponse)
async def get_student_inquiries(
    class_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    try:
        base_key = f"class:{class_id}:student_admission_inquiries"
        version_key = f"{base_key}:version"

        version = await cache.get(version_key)
        version = int(version) if version else 0
        
        cache_key = f"{base_key}:v{version}:page:{page}:size:{page_size}"

        
        cached_data = await cache.get(cache_key)
        
        if cached_data:
            return ResultResponse(
                code=200,
                status="Success",
                message="Student inquiries fetched successfully (cache)",
                result=cached_data
            )

        count_stmt = select(func.count()).where(
            StudentInquiry.class_id == class_id
        )
        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar() or 0

        if total_count == 0:
            return ResultResponse(
                code=404,
                status="failed",
                message="No student inquiries found",
                result={
                    "data": [],
                    "pagination": {
                        "total_count": 0,
                        "page": page,
                        "page_size": page_size,
                        "total_pages": 0,
                        "has_next": False,
                        "has_previous": False
                    }
                }
            )

        total_pages = (total_count + page_size - 1) // page_size

        if page > total_pages:
            return ResultResponse(
                code=400,
                status="failed",
                message="Invalid page number",
                result={}
            )

        offset = (page - 1) * page_size

        stmt = (
            select(StudentInquiry)
            .where(StudentInquiry.class_id == class_id)
            .order_by(StudentInquiry.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )

        result = await db.execute(stmt)
        inquiries = result.scalars().all()

        data = [
            {
                "student_inq_id": inquiry.student_inq_id,
                "student_name": inquiry.student_name,
                "gender": inquiry.gender,
                "guardian_name": inquiry.guardian_name,
                "guardian_phone": inquiry.guardian_phone,
                "guardian_occupation": inquiry.guardian_occupation,
            }
            for inquiry in inquiries
        ]

        response_data = {
            "data": data,
            "pagination": {
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_previous": page > 1
            }
        }

        await cache.set(cache_key, response_data, expire=86400)

        return ResultResponse(
            code=200,
            status="Success",
            message="Student inquiries fetched successfully",
            result=response_data
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )

@student_router.post("/create_student", response_model=ResultResponse)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Check if student_roll_id already exists
        stmt = select(Student).where(Student.student_roll_id == payload.student_roll_id)
        result = await db.execute(stmt)
        existing_student = result.scalars().first()

        if existing_student:
            return ResultResponse(
                code=201,
                status="failed",
                message=f"Student with roll ID {payload.student_roll_id} already exists",
                result={
                    "student_id": existing_student.student_id,
                    "student_name": existing_student.first_name,
                    "gender": existing_student.gender
                }
            )

        # Create new student
        new_student = Student(
            **payload.model_dump(
                exclude_unset=True,
                exclude={"stream_id", "class_id", "enroll_date"}
            )
        )
        db.add(new_student)
        await db.flush()  # flush to get student_id without committing

        # Create class mapping entry
        student_mapping = SchoolClassStudentMapping(
            class_id=payload.class_id,
            student_id=new_student.student_id,
            enroll_date=payload.enroll_date,
            status="enrolled"
        )
        db.add(student_mapping)

        await db.commit()
        
        # CACHE INVALIDATION
        base_key = f"class:{payload.class_id}:students"
        version_key = f"{base_key}:version"

        await cache.incr(version_key)
         
        await db.refresh(new_student)
        await db.refresh(student_mapping)

        return ResultResponse(
            code=201,
            status="Success",
            message="Student created successfully",
            result={
                "student_id": new_student.student_id,
                "mapping_id": student_mapping.id
            }
        )

    except IntegrityError as ie:
        # Handle DB-level constraint errors
        await db.rollback()
        return ResultResponse(
            code=400,
            status="failed",
            message=f"Database integrity error: {str(ie.orig)}"
        )

    except Exception as e:
        # Catch-all for other errors
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )

@student_router.put("/update_student_mapping/{student_id}", response_model=ResultResponse)
async def update_student_mapping(
    student_id: int,
    payload: StudentMappingUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        stmt = select(SchoolClassStudentMapping).where(
            SchoolClassStudentMapping.student_id == student_id
        )
        result = await db.execute(stmt)
        mapping = result.scalars().first()

        if not mapping:
            return ResultResponse(
                code=404,
                status="failed",
                message="Student mapping not found",
                result={}
            )

        old_class_id = mapping.class_id

        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(mapping, key, value)

        await db.commit()
        await db.refresh(mapping)

        # CACHE INVALIDATION
        affected_classes = {old_class_id, mapping.class_id}

        for class_id in affected_classes:
            version_key = f"class:{class_id}:students:version"
            await cache.incr(version_key)

        return ResultResponse(
            code=200,
            status="success",
            message="Student mapping updated successfully",
            result={
                "mapping_id": mapping.id,
                "student_id": mapping.student_id,
                "class_id": mapping.class_id,
                "status": mapping.status
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}",
            result={}
        )

@student_router.get("/get_guardian_list_by_class", response_model=ResultResponse)
async def get_guardian_list_by_class(
    class_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    try:
        
        base_key = f"class:{class_id}:guardian_list"

        
        version_key = f"{base_key}:version"
        version = await cache.get(version_key)
        version = int(version) if version else 1

        
        cache_key = f"{base_key}:v{version}:page:{page}:size:{page_size}"

        
        cached_data = await cache.get(cache_key)
        if cached_data:
            return ResultResponse(
                code=200,
                status="Success",
                message="Guardians fetched successfully (cache)",
                result=cached_data
            )

        
        count_stmt = select(func.count()).select_from(
            Student
        ).join(
            SchoolClassStudentMapping,
            SchoolClassStudentMapping.student_id == Student.student_id
        ).where(
            SchoolClassStudentMapping.class_id == class_id
        )

        total_result = await db.execute(count_stmt)
        total_count = total_result.scalar() or 0

        offset = (page - 1) * page_size

        stmt = select(
            Student.student_id,
            Student.first_name.label("student_name"),
            Student.guardian_first_name,
            Student.guardian_last_name,
            Student.guardian_phone,
            Student.guardian_email,
            Student.guardian_gender
        ).join(
            SchoolClassStudentMapping,
            SchoolClassStudentMapping.student_id == Student.student_id
        ).where(
            SchoolClassStudentMapping.class_id == class_id
        ).offset(offset).limit(page_size)

        result = await db.execute(stmt)
        guardians = result.all()

        guardian_list = [
            {
                "student_id": g.student_id,
                "student_name": g.student_name,
                "guardian_first_name": g.guardian_first_name,
                "guardian_last_name": g.guardian_last_name,
                "guardian_phone": g.guardian_phone,
                "guardian_email": g.guardian_email,
                "guardian_gender": g.guardian_gender
            }
            for g in guardians
        ]

        response_data = {
            "pagination": {
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            },
            "guardian_list": guardian_list,
        }

        
        await cache.set(cache_key, response_data, expire=cache_ttl)

        return ResultResponse(
            code=200,
            status="Success",
            message="Guardians fetched successfully",
            result=response_data
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=str(e)
        )
                
@student_router.post("/bulk_upload_students", response_model=ResultResponse)
async def bulk_upload_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # -------- FILE READ -------- #
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(file.file)
        else:
            return ResultResponse(
                code=400,
                status="failed",
                message="Only CSV or Excel files allowed",
                result={}
            )

        required_columns = ["student_roll_id","first_name","gender","age","class_id","enroll_date"]

        for col in required_columns:
            if col not in df.columns:
                return ResultResponse(
                    code=400,
                    status="failed",
                    message=f"Missing column: {col}",
                    result={}
                )

        students_created = 0
        students_skipped = []
        affected_classes = set()

        # -------- FETCH EXISTING ROLL IDS (OPTIMIZED) -------- #
        roll_ids = df["student_roll_id"].tolist()

        stmt = select(Student.student_roll_id).where(
            Student.student_roll_id.in_(roll_ids)
        )
        result = await db.execute(stmt)
        existing_roll_ids = set(result.scalars().all())

        # -------- LOOP -------- #
        for index, row in df.iterrows():

            if row["student_roll_id"] in existing_roll_ids:
                students_skipped.append(
                    f"Row {index+1}: Roll ID {row['student_roll_id']} already exists"
                )
                continue

            try:
                enroll_date = pd.to_datetime(row["enroll_date"]).date()

                new_student = Student(
                    student_roll_id=row["student_roll_id"],
                    first_name=row["first_name"],
                    gender=row["gender"],
                    age=row["age"],
                    status="active"
                )

                db.add(new_student)
                await db.flush()

                mapping = SchoolClassStudentMapping(
                    class_id=row["class_id"],
                    student_id=new_student.student_id,
                    enroll_date=enroll_date,
                    status="enrolled"
                )

                db.add(mapping)

                affected_classes.add(row["class_id"])
                students_created += 1

            except Exception as row_error:
                students_skipped.append(
                    f"Row {index+1}: {str(row_error)}"
                )
                continue

        await db.commit()

        # -------- CACHE INVALIDATION -------- #
        for class_id in affected_classes:
            version_key = f"class:{class_id}:students:version"
            await cache.incr(version_key)

        return ResultResponse(
            code=201,
            status="Success",
            message="Bulk upload completed",
            result={
                "students_created": students_created,
                "students_skipped": students_skipped
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}",
            result={}
        )

@student_router.get("/get_transfer_student", response_model=ResultResponse)
async def get_transfer_student(
    student_roll_id: int,
    db: AsyncSession = Depends(get_db)
):
    stmt = select(
        Student.student_id,
        Student.student_roll_id,
        Student.first_name.label("student_name"),
        Student.last_name,
        # Mapping fields
        SchoolClassStudentMapping.class_id,
        # Class fields
        SchoolStreamClass.class_code,
        SchoolStreamClass.status.label("class_status"),
        # Stream fields
        SchoolStream.school_stream_id,
        SchoolStream.stream_code,
        SchoolStream.status.label("stream_status")

        ).join(
            SchoolClassStudentMapping,
            SchoolClassStudentMapping.student_id == Student.student_id
        ).join(
            SchoolStreamClass,
            SchoolStreamClass.class_id == SchoolClassStudentMapping.class_id
        ).join(
            SchoolStream,
            SchoolStream.school_stream_id == SchoolStreamClass.school_stream_id
        ).where(
            Student.student_roll_id == student_roll_id
        )

    result = await db.execute(stmt)
    row = result.first()

    # If no student found
    if not row:
        return ResultResponse(
            code=404,
            status="failed",
            message="Student not found",
            result={}
        )

    data = {
        "student_id": row.student_id,
        "student_roll_id": row.student_roll_id,
        "student_name": row.student_name,
        "class_id": row.class_id,
        "class_code": row.class_code,
        "stream_id": row.school_stream_id,
        "stream_code": row.stream_code
    }   

    return ResultResponse(
        code=200,
        status="success",
        message="Student fetched successfully",
        result={"data": data}
    )


@student_router.post("/promote_student", response_model=ResultResponse)
async def promote_student(
    from_class_id: int,
    to_class_id: int,
    db: AsyncSession = Depends(get_db)
):

    # Prevent downgrade
    if to_class_id <= from_class_id:
        return ResultResponse(
            code=400,
            status="failed",
            message="Downgrade is not allowed. Target class must be higher than current class.",
            result={}
        )

    result = await db.execute(
        update(SchoolClassStudentMapping)
        .where(
            SchoolClassStudentMapping.class_id == from_class_id,
            SchoolClassStudentMapping.is_active == 1
        )
        .values(class_id=to_class_id)
    )

    await db.commit()

    if result.rowcount == 0:
        return ResultResponse(
            code=404,
            status="failed",
            message="No students found to promote",
            result={}
        )

    return ResultResponse(
        code=200,
        status="Success",
        message=f"Students promoted from class {from_class_id} to {to_class_id}",
        result={"updated_count": result.rowcount}
    )


@student_router.get("/get_students", response_model=ResultResponse)
async def get_students(
    student_id: int | None = Query(None),
    class_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):

    #  Build Base Key
    base_key = f"class:{class_id or 'all'}:students"
    version_key = f"{base_key}:version"

    version = await cache.get(version_key)
    version = int(version) if version else 0

    cache_key = f"{base_key}:v{version}:page:{page}:size:{page_size}"

    # Check Cache First
    cached_data = await cache.get(cache_key)
    if cached_data:
        return json.loads(cached_data)

    # ---------------- DB QUERY ---------------- #

    query = select(Student).join(
        SchoolClassStudentMapping,
        Student.student_id == SchoolClassStudentMapping.student_id
    )

    count_query = select(func.count()).select_from(Student).join(
        SchoolClassStudentMapping,
        Student.student_id == SchoolClassStudentMapping.student_id
    )

    filters = []

    if student_id:
        filters.append(Student.student_id == student_id)

    if class_id:
        filters.append(SchoolClassStudentMapping.class_id == class_id)

    if filters:
        query = query.where(*filters)
        count_query = count_query.where(*filters)

    # Count
    total_result = await db.execute(count_query)
    total_records = total_result.scalar()

    # Pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    students = result.scalars().all()

    if not students:
        return ResultResponse(
            code=404,
            status="failed",
            message="No students found",
            result={}
        )

    data = [
        {
            "student_id": s.student_id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "gender": s.gender,
            "age": s.age,
            "phone": s.phone,
            "status": s.status
        }
        for s in students
    ]

    response = ResultResponse(
        code=200,
        status="Success",
        message="Students fetched successfully",
        result={
            "data": data,
            "pagination": {
                "total_records": total_records,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_records + page_size - 1) // page_size
            }
        }
    )

    await cache.set(cache_key, json.dumps(response.dict()), ex=300)

    return response