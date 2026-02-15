from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from database.session import get_db
from models.teacher_web_models import Employee,EmployeeRoleClassSubjectMap, Role

from models.admin_models import SchoolStreamClass, SchoolStreamSubject
from schemas.teacher_web_schemas import EmployeeCreate, EmployeeMapping , GetEmployeeMapping, RoleCreate

from schemas.admin_schemas import ResultResponse

from fastapi import Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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


@teacher_router.post("/create_employee", response_model=ResultResponse, status_code=201)
async def create_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db)
):
    try:
        # Check if employee already exists
        result = await db.execute(
            select(Employee).where(Employee.emp_id == payload.emp_id)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Employee with this emp_id already exists"
            )

        employee = Employee(**payload.model_dump())
        db.add(employee)

        await db.commit()
        await db.refresh(employee)

        return ResultResponse(
            code=201,
            status="Success",
            message="Employee created successfully",
            result={
                "id": employee.id,
                "emp_id": employee.emp_id,
                "first_name": employee.first_name,
            },
        )

    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Employee already exists or invalid reference",
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Internal server error",
        )

CLASS_TEACHER = "Class Teacher"
@teacher_router.post("/employee_mapping", response_model=ResultResponse, status_code=201)
async def employee_mapping(
    payload: EmployeeMapping,
    db: AsyncSession = Depends(get_db)
):
    # -------------------- Validate Employee --------------------
    emp = (
        await db.execute(
            select(Employee).where(
                Employee.emp_id == payload.emp_id,
                Employee.first_name == payload.teacher_name
            )
        )
    ).scalar_one_or_none()

    if not emp:
        raise HTTPException(status_code=400, detail="Teacher does not exist")

    # -------------------- Validate Role --------------------
    role = (
        await db.execute(
            select(Role).where(Role.role_name == payload.role_name)
        )
    ).scalar_one_or_none()

    if not role:
        raise HTTPException(status_code=400, detail="Role does not exist")

    # -------------------- Validate Class --------------------
    class_obj = (
        await db.execute(
            select(SchoolStreamClass).where(
                SchoolStreamClass.class_code == payload.class_code
            )
        )
    ).scalar_one_or_none()

    if not class_obj:
        raise HTTPException(status_code=400, detail="Class does not exist")

    # -------------------- Validate Subject (Conditional) --------------------
    subject = None

    if role.role_name != CLASS_TEACHER:
        if not payload.subject_name:
            raise HTTPException(
                status_code=400,
                detail="Subject is required for this role"
            )

        subject = (
            await db.execute(
                select(SchoolStreamSubject).where(
                    SchoolStreamSubject.subject_name == payload.subject_name
                )
            )
        ).scalar_one_or_none()

        if not subject:
            raise HTTPException(status_code=400, detail="Subject does not exist")

    # -------------------- Prevent Duplicate Mapping --------------------
    
    filters = [
        EmployeeRoleClassSubjectMap.emp_id == emp.id,
        EmployeeRoleClassSubjectMap.role_id == role.role_id,
        EmployeeRoleClassSubjectMap.class_id == class_obj.class_id,
    ]

    if subject:
        filters.append(
            EmployeeRoleClassSubjectMap.subject_id == subject.subject_id
        )
    else:
        filters.append(
            EmployeeRoleClassSubjectMap.subject_id.is_(None)
        )

    mapping_exists = (
        await db.execute(
            select(EmployeeRoleClassSubjectMap).where(*filters)
        )
    ).scalar_one_or_none()

    if mapping_exists:
        raise HTTPException(status_code=400, detail="Mapping already exists")

    # -------------------- Create Mapping --------------------
    employee_mapping = EmployeeRoleClassSubjectMap(
        emp_id=emp.id,
        role_id=role.role_id,
        class_id=class_obj.class_id,
        subject_id=subject.subject_id if subject else None,
    )   


    db.add(employee_mapping)

    # -------------------- Update Employee (Single Source of Truth) --------------------
    emp.role_id = role.role_id
    emp.class_id = class_obj.class_id
    emp.subject_id = subject.subject_id if subject else None

    # -------------------- Commit --------------------
    await db.commit()
    await db.refresh(employee_mapping)

    return ResultResponse(
        code=201,
        status="Success",
        message="Employee mapping created successfully",
        result={
            "mapping_id": employee_mapping.map_id
        },
    )


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
    
@teacher_router.get("/get_employees_list", response_model=ResultResponse)
async def get_employees(
    session_yr: str | None = None,
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_db)
):
    try:

        # Enforce ONLY ONE filter
        if session_yr is None and is_active is None:
            raise HTTPException(
                status_code=400,
                detail="Provide either session_yr OR is_active"
            )

        if session_yr is not None and is_active is not None:
            raise HTTPException(
                status_code=400,
                detail="Provide only one filter: session_yr OR is_active"
            )

        query = select(
            Employee,
            Role.role_name,
            SchoolStreamClass.class_name,
            SchoolStreamSubject.subject_name
        ).join(
            EmployeeRoleClassSubjectMap,
            Employee.id == EmployeeRoleClassSubjectMap.emp_id
        ).join(
            Role,
            Role.role_id == EmployeeRoleClassSubjectMap.role_id
        ).join(
            SchoolStreamClass,
            SchoolStreamClass.class_id == EmployeeRoleClassSubjectMap.class_id
        ).join(
            SchoolStreamSubject,
            SchoolStreamSubject.subject_id == EmployeeRoleClassSubjectMap.subject_id
        )

        # Apply ONLY ONE filter
        if session_yr:
            query = query.where(Employee.session_yr == session_yr)

        if is_active is not None:
            query = query.where(Employee.is_active == is_active)

        result = await db.execute(query)
        rows = result.all()
        if not rows:
            raise HTTPException(404, "No employees found")

        data = [
            {
                "id": emp.id,
                "emp_id": emp.emp_id,
                "first_name": emp.first_name,
                "last_name": emp.last_name,
                "session_yr": emp.session_yr,
                "is_active": emp.is_active,
                "role": role,
                "class": cls,
                "subject": sub
            }
            for emp, role, cls, sub in rows
        ]

        return ResultResponse(
            code=200,
            status = "Success",
            message="Employees fetched successfully",
            result={
                "data":data}
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(500, str(e))


