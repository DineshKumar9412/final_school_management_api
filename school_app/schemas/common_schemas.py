from pydantic import BaseModel
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
    
    