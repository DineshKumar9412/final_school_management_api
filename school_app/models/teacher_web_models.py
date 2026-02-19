from sqlalchemy import (
    BigInteger, String, Enum, DateTime, UniqueConstraint,
    ForeignKey, Text, Date, Boolean, Integer, DateTime, LargeBinary, Numeric, DECIMAL,Time
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database.base import Base
from datetime import datetime, date



class Role(Base):
    __tablename__ = "role_creation"

    role_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )
    role_name: Mapped[str | None] = mapped_column(
        String(100),nullable=False,unique=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,default=True,nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),nullable=False)
    
# **************** Employee table*************************

class EmployeeRoleClassSubjectMap(Base):
    __tablename__ = "school_class_emp_mapping"

    map_id: Mapped[int] = mapped_column(
        BigInteger,primary_key=True,autoincrement=True)
    
    emp_id: Mapped[int | None] = mapped_column(
        BigInteger,ForeignKey("employee.id"),nullable=True)
    
    role_id: Mapped[int | None] = mapped_column(
        BigInteger,ForeignKey("role_creation.role_id"),nullable=True)
    class_id: Mapped[int | None] = mapped_column(
        BigInteger,ForeignKey("school_stream_class.class_id"),nullable=True)
    subject_id: Mapped[int | None] = mapped_column(
        BigInteger,ForeignKey("school_stream_subject.subject_id"),nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )
    
class Employee(Base):
    __tablename__ = "employee"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    school_id : Mapped[int | None] = mapped_column(Integer, nullable=True)
    emp_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    DOB: Mapped[date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(
        Enum("male", "female", "other", name="gender_enum"),nullable=True,)
    qualification: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)

    salary: Mapped[float | None] = mapped_column(Numeric(18, 3), nullable=True)
    session_yr: Mapped[str | None] = mapped_column(String(20), nullable=True)
    joining_dt: Mapped[date | None] = mapped_column(Date, nullable=True)
    emp_img: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str | None] = mapped_column(
        Enum("teaching", "non teaching", name="employee_status_enum"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),nullable=False,)
    
