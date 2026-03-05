from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from models.teacher_web_models import Employee,EmployeeRoleClassSubjectMap, Role

from models.admin_models import SchoolStreamClass, SchoolStreamSubject,School
from schemas.teacher_web_schemas import EmployeeCreate, EmployeeUpdate, EmployeeMapping , GetEmployeeMapping, RoleCreate

from schemas.admin_schemas import ResultResponse

from fastapi import Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

import pandas as pd

from database.redis_cache import cache

teacher_router = APIRouter(tags=["WEB API'S FOR TEACHER"])


@teacher_router.get("/get_roles", response_model=ResultResponse)
async def get_roles(db: AsyncSession = Depends(get_db)):
    
    stmt = select(Role).where(Role.is_active == True)
    result = await db.execute(stmt)

    roles = result.scalars().all()

    if not roles:
        return ResultResponse(
            code=404,
            message="No roles found"
        )

    data = []
    for role in roles:
        data.append({
            "role_id": role.role_id,
            "role_name": role.role_name,
            "is_active": role.is_active
        })

    return ResultResponse(
        code=200,
        status = "Success",
        message="Roles fetched successfully",
        result={
            "data": data
        }
    )

# *****************************Teacher Infomation module***************************

@teacher_router.post("/create_employee", response_model=ResultResponse)
async def create_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db)
):
    try:            
        # Check if employee already exists
        exists = await db.scalar(
            select(Employee.id).where(Employee.emp_id == payload.emp_id)
        )

        if exists:
            return ResultResponse(
                code=409,
                status="failed",
                message="Employee already exists",
                result={
                    "Emp_id":payload.emp_id
                }
        )
            
        employee = Employee(**payload.model_dump())
        db.add(employee)

        await cache.delete("school:1:employee:role:meta:{emp_id}")
        
        await db.commit()
        await db.refresh(employee)
        return ResultResponse(
            code=201,
            status="Success",
            message="Employee created successfully",
            result= {
                "id": employee.id,
                "emp_id": employee.emp_id,
                "first_name": employee.first_name,
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error {str(e)}")


@teacher_router.post("/bulk_upload_employees", response_model=ResultResponse)
async def bulk_upload_employees(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    try:
        # -------- READ FILE -------- #
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

        required_columns = [
            "emp_id", "first_name", "last_name", "DOB",
            "gender", "qualification", "mobile",
            "address", "email", "status"
        ]

        for col in required_columns:
            if col not in df.columns:
                return ResultResponse(
                    code=400,
                    status="failed",
                    message=f"Missing column: {col}",
                    result={}
                )

        created_count = 0
        updated_count = 0
        skipped_rows = []

        # -------- FETCH EXISTING EMPLOYEES (NO N+1) -------- #
        emp_ids = df["emp_id"].dropna().tolist()

        result = await db.execute(
            select(Employee).where(Employee.emp_id.in_(emp_ids))
        )
        existing_employees = {emp.emp_id: emp for emp in result.scalars().all()}

        # -------- LOOP -------- #
        for index, row in df.iterrows():
            try:
                emp_id = int(row["emp_id"])

                employee_data = {
                    "emp_id": emp_id,
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "DOB": pd.to_datetime(row["DOB"]).date(),
                    "gender": row["gender"],
                    "qualification": row["qualification"],
                    "mobile": row["mobile"],
                    "address": row["address"],
                    "email": row["email"],
                    "salary": row.get("salary"),
                    "session_yr": row.get("session_yr"),
                    "joining_dt": pd.to_datetime(row["joining_dt"]).date() if pd.notna(row.get("joining_dt")) else None,
                    "status": row["status"],
                    "is_active": row.get("is_active", True),
                }

                if emp_id in existing_employees:
                    # UPDATE
                    employee = existing_employees[emp_id]
                    for key, value in employee_data.items():
                        setattr(employee, key, value)
                    updated_count += 1
                else:
                    # CREATE
                    new_employee = Employee(**employee_data)
                    db.add(new_employee)
                    created_count += 1

            except Exception as row_error:
                skipped_rows.append(
                    f"Row {index+1}: {str(row_error)}"
                )
                continue

        await db.commit()

        # -------- CACHE INVALIDATION -------- #
        await cache.delete("school:1:employee:role:meta:all")

        return ResultResponse(
            code=200,
            status="Success",
            message="Bulk employee upload completed",
            result={
                "created": created_count,
                "updated": updated_count,
                "skipped": skipped_rows
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error {str(e)}",
            result={}
        )
        
@teacher_router.put("/update_employee/{emp_id}", response_model=ResultResponse)
async def update_employee(
    emp_id: int,
    payload: EmployeeUpdate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # 1. Fetch existing employee
        employee = await db.scalar(
            select(Employee).where(Employee.emp_id == emp_id)
        )

        if not employee:
            return ResultResponse(
                code=404,
                status="failed",
                message="Employee not found",
                result={"emp_id": emp_id}
            )

        # 2. Get only provided fields
        update_data = payload.model_dump(exclude_unset=True)

        if not update_data:
            return ResultResponse(
                code=400,
                status="failed",
                message="No data provided for update"
            )
        
        # 3. Clear related cache
        await cache.delete(f"school:1:employee:emp_id:{emp_id}")
        await cache.delete(f"school:1:employee:name:{employee.first_name}")
        
        # 4. Allow only safe fields to be updated
        ALLOWED_FIELDS = {
            "first_name", "last_name", "DOB", "gender", "qualification",
            "mobile", "address", "email", "salary", "session_yr",
            "joining_dt", "status", "is_active"
        }
        for key, value in update_data.items():
            if key in ALLOWED_FIELDS:
                setattr(employee, key, value)
        
        # 5. Save changes
        await db.commit()
        await db.refresh(employee)

        return ResultResponse(
            code=200,
            status="success",
            message="Employee updated successfully",
            result={
                "id": employee.id,
                "emp_id": employee.emp_id,
                "first_name": employee.first_name,
            }
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}"
        )

@teacher_router.get("/get_employees_list", response_model=ResultResponse)
async def get_employees_list(
    school_id: int,
    emp_id: Optional[int] = None,
    teacher_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    try:
        # -------------------- Validation --------------------
        if emp_id is None and teacher_name is None:
            return ResultResponse(
                code=400,
                status="failed",
                message="Either emp_id or teacher_name is required",
            )

        # -------------------- Cache Key --------------------
        if emp_id is not None:
            cache_key = f"school:{school_id}:employee:emp_id:{emp_id}"
        else:
            cache_key = f"school:{school_id}:employee:name:{teacher_name}"

        # -------------------- Try Cache --------------------
        cached_data = await cache.get(cache_key)
        if cached_data:
            return ResultResponse(
                code=200,
                status="success",
                message="Employees fetched from cache",
                result={
                    "cache": True,
                    "data": cached_data,
                },
            )
        # -------------------- Employee Query --------------------
        if emp_id is not None:
            stmt = select(Employee).where(
                Employee.school_id == school_id,
                Employee.emp_id == emp_id
            )
        else:
            stmt = select(Employee).where(
                Employee.school_id == school_id,
                Employee.first_name == teacher_name
            )

        result = await db.execute(stmt)
        employees = result.scalars().all()
        
        if not employees:
            return ResultResponse(
                code=404,
                status="failed",
                message="No employees found",
            )

        # -------------------- Roles --------------------
        role_result = await db.execute(select(Role))
        roles = role_result.scalars().all()
        

        # -------------------- Response Data --------------------
        data = {
            "employees": [
                {
                    "id": emp.id,
                    "emp_id": emp.emp_id,
                    "first_name": emp.first_name,
                }
                for emp in employees
            ],
            "roles": [
                {
                    "id": role.role_id,
                    "role_name": role.role_name,
                }
                for role in roles
            ],
        }
        # -------------------- Store Cache --------------------
        await cache.set(cache_key, data, expire=600)

        return ResultResponse(
            code=200,
            status="success",
            message="Employees fetched successfully",
            result=data,
        )

    except Exception as e:
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error: {str(e)}",
        )

@teacher_router.post("/employee_mapping",response_model=ResultResponse)
async def employee_mapping(
    payload: EmployeeMapping,
    db: AsyncSession = Depends(get_db)
):
    try:
        # -------------------- Check Employee --------------------
        employee = await db.scalar(
            select(Employee).where(
                Employee.emp_id == payload.emp_id,
                Employee.first_name == payload.emp_name
            )
        )

        if not employee:
            return ResultResponse(
                code=404,
                status="failed",
                message="Employee does not exist",
                result={
                    "emp_id": payload.emp_id,
                    "emp_name": payload.emp_name,
                },
            )

        # -------------------- Check Existing Mapping --------------------
        map_exist = await db.scalar(
            select(EmployeeRoleClassSubjectMap).where(
                EmployeeRoleClassSubjectMap.emp_id == employee.id,
                EmployeeRoleClassSubjectMap.subject_id == payload.subject_id
            )
        )

        if map_exist:
            return ResultResponse(
                code=409,
                status="failed",
                message="Employee subject mapping already exists",
                result={
                    "emp_id": payload.emp_id,
                    "emp_name": payload.emp_name,
                    "subject_id": payload.subject_id
                },
            )

        # -------------------- Create Mapping --------------------
        employee_mapping = EmployeeRoleClassSubjectMap(
            emp_id=employee.id,
            role_id=payload.role_id,
            class_id=payload.class_id,
            subject_id=payload.subject_id,
        )

        db.add(employee_mapping)
        await db.commit()
        await db.refresh(employee_mapping)

        return ResultResponse(
            code=201,
            status="success",
            message="Employee mapping created successfully",
            result={
                "id": employee_mapping.map_id,
                "emp_id": employee.emp_id,
                "role_id": employee_mapping.role_id,
                "class_id": employee_mapping.class_id,
                "subject_id": employee_mapping.subject_id,
            },
        )

    except Exception as e:
        await db.rollback()
        return ResultResponse(
            code=500,
            status="failed",
            message=f"Internal server error {str(e)}")


@teacher_router.get("/get_employee_mapping_list", response_model=ResultResponse)
async def get_employee_mapping_list(
    payload:GetEmployeeMapping,
    db: AsyncSession = Depends(get_db)
):
    data = {
        "class_code" :None,
        "Section": None,
        "Class Teacher" :None,
        "Subject Teacher":None
    }
    class_sub_obj = (
        await db.execute(
            select(EmployeeRoleClassSubjectMap).where(
                EmployeeRoleClassSubjectMap.class_code == payload.class_code,
                EmployeeRoleClassSubjectMap.Section == payload.Section
            )
        )
    ).scalar_one_or_none()

    if not class_sub_obj:
        raise HTTPException(status_code=400, detail="Class does not exist")
    

