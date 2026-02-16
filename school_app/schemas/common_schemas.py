from pydantic import BaseModel,validator, Field
from typing import Optional
from datetime import datetime, date,time


class NotificationCreate(BaseModel):
    title: str
    message: Optional[str] = None
    role_id: Optional[int] = None
    image: Optional[bytes] = None
    
class TimetableCreate(BaseModel):
    class_id: Optional[int]
    school_group_id: Optional[int]
    subject_id: Optional[int]
    type: Optional[str]
    date: Optional[date]
    start_time: time
    end_time: time
    start_ampm:str
    end_ampm:str
    duration: int
    day: Optional[str]
    
class AnnouncementCreate(BaseModel):
    class_id: int | None = None
    title: str | None = None
    description: str | None = None
    url: str | None = None
    
class HolidayCreate(BaseModel):
    holiday_date: date
    title: str
    description: str | None = None
    
class StudentDiaryCreate(BaseModel):
    student_id: int
    class_id: int | None = None
    subject_id: int | None = None
    task_title: str | None = None
    dairy_date: date | None = None
    status: str | None = None

class TimetableResponse(BaseModel):
    day: Optional[str]
    start_time: str
    end_time: str
    subject_name: str
    class_name: str

    @validator("start_time", "end_time", pre=True)
    def serialize_time(cls, v):
        if isinstance(v, time):
            return v.isoformat()
        return v

class CustomAlarmCreate(BaseModel):
    stream_id: Optional[int] = None
    class_id: Optional[int] = None
    message: Optional[str] = Field(default=None, max_length=1000)
    alarm_date: date
    slot_time: Optional[str] = Field(default=None, max_length=10)
