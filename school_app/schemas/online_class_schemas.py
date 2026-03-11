# online_class_schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OnlineClassCreate(BaseModel):
    school_id: int
    class_id: int
    subject_id: Optional[int] = None
    title: str = Field(..., max_length=200)
    meeting_link: str = Field(..., max_length=500)
    scheduled_at: datetime
    duration_min: Optional[int] = Field(60, description="Duration in minutes")


class OnlineClassUpdate(BaseModel):
    subject_id: Optional[int] = None
    title: Optional[str] = Field(None, max_length=200)
    meeting_link: Optional[str] = Field(None, max_length=500)
    scheduled_at: Optional[datetime] = None
    duration_min: Optional[int] = None
