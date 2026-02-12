#admin models.py
from sqlalchemy import (
    BigInteger, String, Enum, DateTime, UniqueConstraint,
    ForeignKey, Text, Date, Boolean, Integer, DateTime, LargeBinary, Numeric, DECIMAL,Time
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database.base import Base
from datetime import datetime, date


class School(Base):
    __tablename__ = "school"

    school_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True, autoincrement=True
    )
    school_name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), unique=True)
    email: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    website: Mapped[str | None] = mapped_column(String(255))
    address_line1: Mapped[str | None] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))

    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="school_status"),
        default="active"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["SchoolUser"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    streams: Mapped[list["SchoolStream"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )
    classes: Mapped[list["SchoolStreamClass"]] = relationship(
        back_populates="school", cascade="all, delete-orphan"
    )

class SchoolUser(Base):
    __tablename__ = "school_user"
    __table_args__ = (
        UniqueConstraint("school_id", "email", name="uk_school_user_email"),
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True, autoincrement=True
    )
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("school.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(150), nullable=False,unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[str] = mapped_column(
        Enum("admin", "instructor", "staff", name="academy_user_role"),
        nullable=False,
        default="staff"
    )

    phone: Mapped[str | None] = mapped_column(String(30),unique=True)
    address_line1: Mapped[str | None] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))

    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="academy_user_status"),
        default="active"
    )

    last_login_at: Mapped[DateTime | None] = mapped_column(DateTime)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    school: Mapped["School"] = relationship(back_populates="users")

class SchoolGroup(Base):
    __tablename__ = "school_group"

    school_group_id: Mapped[int] = mapped_column(BigInteger,primary_key=True,
        autoincrement=True,
    )

    school_id: Mapped[int] = mapped_column(BigInteger,ForeignKey("school.school_id"),
        nullable=False,
        index=True,
    )
    group_name: Mapped[str] = mapped_column(String(200),nullable=False,)
    description: Mapped[str | None] = mapped_column(Text,nullable=True,)
    start_date: Mapped[date | None] = mapped_column(Date,nullable=True,)
    end_date: Mapped[date | None] = mapped_column(Date,nullable=True,)
    validity_days: Mapped[int | None] = mapped_column(Integer,nullable=True,)
    status: Mapped[str | None] = mapped_column(
        Enum(
            "draft",
            "active",
            "inactive",
            "archived",
            name="school_group_status",
        ),
        server_default="draft",
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

class SchoolStream(Base):
    __tablename__ = "school_stream"

    school_stream_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True, autoincrement=True
    )
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("school.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    school_group_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("school_group.school_group_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    stream_name: Mapped[str] = mapped_column(String(200), nullable=False)
    stream_code: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    validity_days: Mapped[int | None] = mapped_column(Integer)

    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    max_students: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "inactive", "archived", name="school_stream_status"),
        default="draft"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    school: Mapped["School"] = relationship(back_populates="streams")
    classes: Mapped[list["SchoolStreamClass"]] = relationship(
        back_populates="school_stream", cascade="all, delete-orphan"
    )
    subjects: Mapped[list["SchoolStreamSubject"]] = relationship(
        back_populates="school_stream", cascade="all, delete-orphan"
    )

class SchoolStreamClass(Base):
    __tablename__ = "school_stream_class"

    class_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True, autoincrement=True
    )

    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("school.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    school_stream_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("school_stream.school_stream_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    class_name: Mapped[str] = mapped_column(String(200), nullable=False)
    class_code: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)

    start_date: Mapped[Date | None] = mapped_column(Date)
    end_date: Mapped[Date | None] = mapped_column(Date)
    validity_days: Mapped[int | None] = mapped_column(Integer)

    schedule_info: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[str] = mapped_column(
        Enum(
            "scheduled", "running", "completed", "cancelled",
            name="school_stream_class_status"
        ),
        default="scheduled"
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    school: Mapped["School"] = relationship(back_populates="classes")
    school_stream: Mapped["SchoolStream"] = relationship(back_populates="classes")

class SchoolStreamSubject(Base):
    __tablename__ = "school_stream_subject"

    subject_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, index=True, autoincrement=True
    )

    school_stream_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("school_stream.school_stream_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    subject_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        Enum("active", "inactive", name="school_stream_subject_status"),
        default="active"
    )

    sort_order: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationship
    school_stream: Mapped["SchoolStream"] = relationship(back_populates="subjects")
