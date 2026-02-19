from pydantic import BaseModel
from typing import Optional, Literal,List
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
    
class EmployeeAttendanceCreate(BaseModel):
    school_group_id: Optional[int] = None
    emp_id: int
    attendance_dt: date
    status: Optional[Literal["P", "A", "L"]] = "P"
    
class StudentAttendanceCreate(BaseModel):
    class_id: Optional[int] = None
    section: Optional[str] = None
    school_group_id: Optional[int] = None
    student_id: int
    attendance_dt: date
    status: Optional[Literal["P", "A", "L"]] = "P"
    
    
class StudentAttendanceItem(BaseModel):
    student_id: int
    status: Optional[Literal["P", "A", "L"]] = None    
    
class StudentAttendanceBulkCreate(BaseModel):
    class_id: int
    section: Optional[str] = None
    school_group_id: Optional[int] = None
    attendance_dt: date
    students: List[StudentAttendanceItem]
    
    
class EmployeeAttendanceItem(BaseModel):
    emp_id: int
    status: Optional[Literal["P", "A", "L"]] = None


class EmployeeAttendanceBulkCreate(BaseModel):
    school_group_id: Optional[int] = None
    attendance_dt: date
    employees: List[EmployeeAttendanceItem]