from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from models.student_web_models import StudentInquiry, Student, SchoolClassStudentMapping

from schemas.student_web_schemas import StudentInquiryCreate, StudentCreate

from schemas.admin_schemas import ResultResponse
from fastapi import Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import Optional

from database.redis_cache import cache

import pandas as pd

student_router = APIRouter(tags=["WEB API'S FOR STUDENT"])


@student_router.post("/student_admission_inquiries", response_model=ResultResponse, status_code=201)   
async def student_admission_inquiries(schoolinquiry_payload: StudentInquiryCreate, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(StudentInquiry).where(
            StudentInquiry.guardian_phone == schoolinquiry_payload.guardian_phone
        )
        result = await db.execute(stmt)
        existing_inquiry = result.scalars().first()

        # ✅ Check if already exists
        if existing_inquiry:
            return ResultResponse(
                code=201,
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
        cache_key = f"class:{schoolinquiry_payload.class_id}:student_admission_inquiries:meta"
        await cache.delete(cache_key)
        
        new_inquiry = StudentInquiry( **schoolinquiry_payload.model_dump(exclude_unset=True))
        db.add(new_inquiry)
        await db.commit()
        await db.refresh(new_inquiry)

        return ResultResponse(
            code=201,
            status = "Success",
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


@student_router.get("/get_student_admission_inquiries",response_model=ResultResponse)
async def get_student_inquiries(
    class_id: int,
    db: AsyncSession = Depends(get_db)
):
    cache_key = f"class:{class_id}:student_admission_inquiries:meta"
    res_cached = await cache.get(cache_key)
    if res_cached:
        return ResultResponse(
            code=200,
            status="Success",
            message="Student inquiries fetched successfully(cache)",
            result={"data": res_cached}
    )
    stmt = (
        select(StudentInquiry)
        .where(StudentInquiry.class_id == class_id)
        .order_by(StudentInquiry.created_at.desc())
    )

    result = await db.execute(stmt)
    inquiries = result.scalars().all()

    if not inquiries:
        return ResultResponse(
            code=404,
            status="failed",
            message="No student inquiries found",
            result={"data": []}
        )

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
    
    await cache.set(cache_key, value=data, expire=600)
    
    return ResultResponse(
        code=200,
        status="Success",
        message="Student inquiries fetched successfully",
        result={"data": data}
    )


@student_router.post("/create_student", response_model=ResultResponse, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(Student).where(
            Student.student_roll_id == Student.student_roll_id
        )
        result = await db.execute(stmt)
        student_existing = result.scalars().first()

        # ✅ Check if already exists
        if student_existing:
            return ResultResponse(
                code=201,
                status="failed",
                message="Student Already Exists",
                result={
                    "student_roll_id": student_existing.student_inq_id,
                    "student_name": student_existing.first_name,
                    "gender": student_existing.gender
                }
            )
        
        new_student = Student(**payload.model_dump(exclude_unset=True,exclude={"stream_id", "class_id"}))
        db.add(new_student)
        await db.commit()
        await db.refresh(new_student)

        # create mapping entry
        student_mapping = SchoolClassStudentMapping(
            class_id=payload.class_id,
            
            student_id=new_student.student_id,
            enroll_date=payload.enroll_date,
        )

        db.add(student_mapping)
        await db.commit()
        await db.refresh(student_mapping)
        
        return ResultResponse(
            code=201,
            status = "Success",
            message="Student created successfully",
            result={"student_id": new_student.student_id}
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )


# TODO need to work
@student_router.get("/get_students", response_model=ResultResponse)
async def get_students(db: AsyncSession = Depends(get_db)):
    student_id = ""
    result = await db.execute(select(Student).where(Student.student_id == student_id))
    students = result.scalar_one_or_none()


    if not students:
        return ResultResponse(code=404, message="No students found")

    data = []
    for s in students:
        data.append({
            "student_id": s.student_id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "gender": s.gender,
            "age": s.age,
            "phone": s.phone,
            "status": s.status
        })

    return ResultResponse(code=200,status = "Success", message="Students fetched successfully", result={"data": data})


@student_router.get("/get_guardian_list", response_model=ResultResponse)
async def get_guardian_list(db: AsyncSession = Depends(get_db)):
    pass

# class , class session

@student_router.post("/bulk_upload_students", response_model=ResultResponse)
async def bulk_upload_students(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Read file
        if file.filename.endswith(".csv"):
            df = pd.read_csv(file.file)
        elif file.filename.endswith(".xlsx"):
            df = pd.read_excel(file.file)
        else:
            raise HTTPException(status_code=400, detail="Only CSV or Excel files allowed")


        # Required columns validation
        required_columns = ["first_name", "gender", "age"]
        for col in required_columns:
            if col not in df.columns:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing column: {col}"
                )
                
        # Convert DataFrame to dict
        students_data = df.to_dict(orient="records")

        students = []
        for row in students_data:
            student = Student(
                first_name=row.get("first_name"),
                last_name=row.get("last_name"),
                gender=row.get("gender"),
                dob=row.get("dob"),
                age=row.get("age"),
                email=row.get("email"),
                phone=row.get("phone"),
                address_line1=row.get("address_line1"),
                city=row.get("city"),
                state=row.get("state"),
                country=row.get("country"),
                postal_code=row.get("postal_code"),
                guardian_first_name=row.get("guardian_first_name"),
                guardian_phone=row.get("guardian_phone"),
                status=row.get("status", "active"),
            )
            students.append(student)

        db.add_all(students)
        await db.commit()

        return ResultResponse(
            code=201,
            status = "Success",
            message=f"{len(students)} students uploaded successfully"
        )

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database error")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@student_router.get("/transfer_student", response_model=ResultResponse)
async def transfer_student(db: AsyncSession = Depends(get_db)):
    student_name = ""
    result = await db.execute(select(Student).where(Student.student_name == student_name))
    students = result.scalar_one_or_none()

    if not students:
        return ResultResponse(code=404, message="No students found")

    data = []
    for s in students:
        data.append({
            "student_id": s.student_id,
            "first_name": s.first_name,
            "last_name": s.last_name,
            "gender": s.gender,
            "age": s.age,
            "phone": s.phone,
            "status": s.status
        })

    return ResultResponse(code=200, message="Students fetched successfully", result={"data": data})

@student_router.get("/promote_student", response_model=ResultResponse)
async def promote_student(db: AsyncSession = Depends(get_db)):
    pass

