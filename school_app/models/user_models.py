from database.base import Base
from sqlalchemy import String, DateTime, ForeignKey, Boolean, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import ClassVar


class DeviceRegistration(Base):
    __tablename__ = "device_registration"

    id:            Mapped[int]        = mapped_column(primary_key=True, autoincrement=True)
    device_id:     Mapped[str]        = mapped_column(String(128), unique=True, nullable=False)
    os:            Mapped[str]        = mapped_column(String(20), nullable=False)
    os_version:    Mapped[str | None] = mapped_column(String(20), nullable=True)
    make:          Mapped[str | None] = mapped_column(String(50), nullable=True)
    model:         Mapped[str | None] = mapped_column(String(50), nullable=True)
    app_version:   Mapped[str | None] = mapped_column(String(20), nullable=True)
    fcm_token:     Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active:     Mapped[bool]       = mapped_column(Boolean, default=True, nullable=False)
    registered_at: Mapped[DateTime]   = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at:    Mapped[DateTime]   = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

class Session(Base):
    __tablename__ = "session"

    id:          Mapped[int]        = mapped_column(primary_key=True, autoincrement=True)
    device_id:   Mapped[int]        = mapped_column(
        ForeignKey("device_registration.id", name="fk_session_device"), nullable=False)
    user_id:     Mapped[str | None] = mapped_column(String(128), nullable=True)
    role:        Mapped[str | None] = mapped_column(String(20), nullable=True)
    client_key:  Mapped[str]        = mapped_column(String(255), nullable=False)
    valid_till:  Mapped[DateTime]   = mapped_column(DateTime, nullable=False)
    created_on:  Mapped[DateTime]   = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False)
    modified_on: Mapped[DateTime]   = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    device: Mapped["DeviceRegistration"] = relationship("DeviceRegistration", backref="sessions")
    user: ClassVar[dict | None] = None

class FcmToken(Base):
    __tablename__ = "fcm_token"

    id:         Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[int | None] = mapped_column(Integer, nullable=True)
    class_id:   Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role:       Mapped[str | None] = mapped_column(String(20), nullable=True)
    fcm_token:  Mapped[str | None] = mapped_column(String(255), nullable=True)

class OtpVerification(Base):
    __tablename__ = "otp_verification"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    identifier: Mapped[str]      = mapped_column(String(128), nullable=False)
    otp:        Mapped[str]      = mapped_column(String(6), nullable=False)
    is_used:    Mapped[bool]     = mapped_column(Boolean, default=False, nullable=False)
    attempts:   Mapped[int]      = mapped_column(Integer, default=0, nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.current_timestamp(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)