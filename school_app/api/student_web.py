from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from models.student_web_models import StudentInquiry, Student

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
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Database constraint violation"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e) 
        )


@student_router.get("/get_student_admission_inquiries", response_model=ResultResponse)
async def get_student_inquiries(class_id:int,db: AsyncSession = Depends(get_db)):
    
    stmt = select(StudentInquiry).where(StudentInquiry.class_id == class_id)
    result = await db.execute(stmt)

    inquiries = result.scalars().all()

    if not inquiries:
        return ResultResponse(
            code=404,
            message="No student inquiries found"
        )

    data = []
    for inquiry in inquiries:
        data.append({
            "student_inq_id": inquiry.student_inq_id,
            "student_name": inquiry.student_name,
            "gender": inquiry.gender,
            "age": inquiry.age,
            "class_id": inquiry.class_id,
            "guardian_name": inquiry.guardian_name,
            "guardian_phone": inquiry.guardian_phone,
            "guardian_occupation": inquiry.guardian_occupation,
            "created_at": inquiry.created_at,
        })

    return ResultResponse(
        code=200,
        status = "Success",
        message="Student inquiries fetched successfully",
        result={
            "data": data
        }
    )


@student_router.post("/create_student", response_model=ResultResponse, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    try:
        new_student = Student(**payload.model_dump(exclude_unset=True))
        db.add(new_student)
        await db.commit()
        await db.refresh(new_student)

        return ResultResponse(
            code=201,
            status = "Success",
            message="Student created successfully",
            result={"student_id": new_student.student_id}
        )

    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Database constraint violation")

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


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

