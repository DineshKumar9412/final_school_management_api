# banner_models.py
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from database.base import Base
from datetime import datetime


class SchoolBanner(Base):
    __tablename__ = "school_banner"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True
    )
    school_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("school.school_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    bannerlink: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, comment="1 = active, 0 = inactive"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
