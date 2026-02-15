from pydantic import BaseModel,Field
from typing import Optional
from datetime import datetime,date,time



class GradeCreate(BaseModel):
    start_range: float
    end_range: float
    grade: Optional[str] = Field(None, max_length=10)
   
    
class ExamCreate(BaseModel):
    exam_name: str
    class_id: int
    session_yr: str
    exam_description: str
    is_active: Optional[bool] = True
    
    
class ExamTimetableCreate(BaseModel):
    exam_id: int
    class_id: int
    group_id: int
    subject_id: int
    total_marks: float
    pass_mark: float
    exam_start_date: datetime
    exam_end_date: Optional[datetime] = None
    start_time : time
    end_time : time
    start_ampm : str
    end_ampm:str
    is_active: Optional[bool] = True
    
    
    
class StudentMarksCreate(BaseModel):
    student_id: int
    class_id: int
    subject_id: int
    grade_id: int
    
class OnlineExamCreate(BaseModel):
    class_id: int
    subject_id: int
    exam_code: str | None = None
    url: str | None = None
    duration: str | None = None
    start_date: date
    end_date: date
    
    
class OnlineClassCreate(BaseModel):
    class_id: int
    subject_id: int
    url: str | None = None
    duration: str | None = None
    start_date: date
    end_date: date