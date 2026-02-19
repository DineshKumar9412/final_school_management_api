from sqlalchemy import (
    BigInteger, String, Enum, DateTime, UniqueConstraint,
    ForeignKey, Text, Date, Boolean, Integer, DateTime, LargeBinary, Numeric, DECIMAL,Time,text
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from database.base import Base
from datetime import datetime, date


class StudentInquiry(Base):
    __tablename__ = "student_admission_inquiry"

    student_inq_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_name: Mapped[str] = mapped_column(String(100), nullable=False)
    gender: Mapped[str] = mapped_column(Enum("male", "female", "other", name="gender_enum"),nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    class_id: Mapped[int] = mapped_column(Integer, nullable=True)
    guardian_name: Mapped[str] = mapped_column(String(150), nullable=True)
    guardian_phone: Mapped[str] = mapped_column(String(30), nullable=True)
    guardian_occupation: Mapped[str] = mapped_column(String(150), nullable=True)
    guardian_gender: Mapped[str] = mapped_column(Enum("male", "female", "other", name="guardian_gender_enum"),nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),nullable=False)

class Student(Base):
    __tablename__ = "students" 

    student_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_inq_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    student_roll_id = Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=True)
    gender: Mapped[str] = mapped_column(Enum("male", "female", "other", name="student_gender_enum"),nullable=True)
    dob: Mapped[Date] = mapped_column(Date, nullable=True)
    age: Mapped[int] = mapped_column(Integer, nullable=True)
    email: Mapped[str] = mapped_column(String(150), nullable=True)
    phone: Mapped[str] = mapped_column(String(30), nullable=True)
    address_line1: Mapped[str] = mapped_column(String(200), nullable=True)
    address_line2: Mapped[str] = mapped_column(String(200), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=True)
    state: Mapped[str] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str] = mapped_column(String(20), nullable=True)
    blood_group: Mapped[str] = mapped_column(String(10), nullable=True)
    emergency_contact: Mapped[str] = mapped_column(String(30), nullable=True)
    stu_image: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    guardian_first_name: Mapped[str] = mapped_column(String(150), nullable=True)
    guardian_last_name: Mapped[str] = mapped_column(String(150), nullable=True)
    guardian_phone: Mapped[str] = mapped_column(String(30), nullable=True)
    guardian_email: Mapped[str] = mapped_column(String(150), nullable=True)
    guardian_gender: Mapped[str] = mapped_column(Enum("male", "female", "other", name="guardian_gender_enum"),nullable=True)
    guardian_image: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(Enum("active", "inactive", name="student_status_enum"),default="active",nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),nullable=False)



class SchoolClassStudentMapping(Base):
    __tablename__ = "school_class_student_mapping"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    enroll_date: Mapped[str] = mapped_column(Date, nullable=False)
    valid_from_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    valid_to_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool | None] = mapped_column(Boolean,nullable=True,server_default=text("1"))
    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="student_status_enum"),
        nullable=True,server_default=text("'active'"))
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),nullable=False)
