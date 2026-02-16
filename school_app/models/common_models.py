
from sqlalchemy import (BigInteger, String, DateTime,ForeignKey, DateTime, LargeBinary,Date,Time,Integer, Enum)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from database.base import Base
from typing import Optional


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(BigInteger,primary_key=True,autoincrement=True,)
    title: Mapped[str] = mapped_column(String(100),nullable=False,)
    message: Mapped[str | None] = mapped_column(String(10000),nullable=True,)
    role_id: Mapped[int | None] = mapped_column(BigInteger,ForeignKey("role_creation.role_id"),nullable=True,)
    image: Mapped[bytes | None] = mapped_column(LargeBinary,nullable=True,)
    created_at: Mapped[DateTime] = mapped_column(DateTime,nullable=False,server_default=func.current_timestamp(),)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,nullable=False,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),)
    
class Announcement(Base):
    __tablename__ = "announcement"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id: Mapped[int | None] = mapped_column(
        BigInteger,ForeignKey("school_stream_class.class_id", name="fk_announce_class"),nullable=True)
    title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    file: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime,server_default=func.current_timestamp(),nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),nullable=False)
    
class Holiday(Base):
    __tablename__ = "holiday"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    holiday_date: Mapped[Date] = mapped_column(Date, nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),nullable=False)
    
class StudentDiary(Base):
    __tablename__ = "student_diary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("student.student_id", name="fk_stu_diary"),nullable=False)
    class_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    subject_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    task_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dairy_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str | None] = mapped_column(String(1), nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime,server_default=func.current_timestamp(),nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),nullable=False)
    
class SchoolClassStudentMapping(Base):
    __tablename__ = "school_class_student_mapping"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    enroll_date: Mapped[Date] = mapped_column(Date, nullable=False)
    valid_from_date: Mapped[Date] = mapped_column(Date, nullable=True)
    valid_to_date: Mapped[Date] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Integer, default=1, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("enrolled", "completed", "dropped", name="student_enrollment_status_enum"),
        default="enrolled",
        nullable=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), 
        onupdate=func.current_timestamp(), nullable=False
    )

class TimeTable(Base):
    __tablename__ = "time_table"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    class_id: Mapped[int | None] = mapped_column(BigInteger,ForeignKey("school_stream_class.class_id"),nullable=True,)
    school_group_id: Mapped[int | None] = mapped_column(BigInteger,ForeignKey("school_group.school_group_id"),nullable=True,)
    subject_id: Mapped[int | None] = mapped_column(BigInteger,ForeignKey("school_stream_subject.subject_id"),nullable=True,)
    type: Mapped[str | None] = mapped_column(String(1),comment="S - Student , E - Employee",)
    date: Mapped[Date | None] = mapped_column(Date)
    start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    start_ampm: Mapped[str] = mapped_column(String(2), nullable=False, comment="AM / PM")
    end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    end_ampm: Mapped[str] = mapped_column(String(2), nullable=False, comment="AM / PM")
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    day: Mapped[str | None] = mapped_column(String(10))
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,server_default=func.current_timestamp(),onupdate=func.current_timestamp(),nullable=False)

class CustomAlarm(Base):
    __tablename__ = "custom_alarm"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True
    )
    stream_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("school_stream.school_stream_id"),
        nullable=True,
    )
    class_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        ForeignKey("school_stream_class.class_id"),
        nullable=True,
    )
    message: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )
    alarm_date: Mapped[Date | None] = mapped_column(Date)
    slot_time: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )