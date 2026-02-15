
from sqlalchemy import (
    BigInteger, String, Enum, DateTime, UniqueConstraint,
    ForeignKey, Text, Date, Boolean, Integer, DateTime, LargeBinary, Numeric, DECIMAL,Time
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from database.base import Base
from datetime import datetime, date

class VehicleDetails(Base):
    __tablename__ = "vehicle_details"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    vehicle_no: Mapped[str] = mapped_column(String(15), nullable=True)
    vehicle_capacity: Mapped[int] = mapped_column(Integer, nullable=True)
    vehicle_reg_no: Mapped[str] = mapped_column(String(15), nullable=True)
    status: Mapped[str] = mapped_column(String(1), nullable=True)
    driver_name: Mapped[str] = mapped_column(String(50), nullable=False)
    helper_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_no: Mapped[str] = mapped_column(String(15), nullable=True)
    distance: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(1), nullable=True)
    pick_start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    pick_end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    drop_start_time: Mapped[Time] = mapped_column(Time, nullable=False)
    drop_end_time: Mapped[Time] = mapped_column(Time, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

class VehicleRouteMap(Base):
    __tablename__ = "vehicle_routes_map"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    route_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("routes.id")
    )

    vehicle_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehicle_details.id")
    )

    driver_name: Mapped[str] = mapped_column(String(50), nullable=False)

    helper_name: Mapped[str] = mapped_column(String(50), nullable=False)

    driver_mob_no: Mapped[str] = mapped_column(String(15), nullable=True)

    helper_mob_no: Mapped[str] = mapped_column(String(15), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

class TransportationStudent(Base):
    __tablename__ = "transportation_student"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )

    vehicle_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehicle_details.id")
    )

    class_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("school_stream_class.class_id")
    )

    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("student.student_id")
    )

    group_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("school_group.group_id")
    )

    session_yr: Mapped[str] = mapped_column(String(10), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

class VehicleExpense(Base):
    __tablename__ = "vehicle_expenses"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    vehicle_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("vehicle_details.id")
    )
    session_yr: Mapped[str] = mapped_column(String(10), nullable=True)
    amount: Mapped[float] = mapped_column(DECIMAL(18, 2), nullable=True)
    date: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    image: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)
    description: Mapped[str] = mapped_column(String(100), nullable=True)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False
    )

