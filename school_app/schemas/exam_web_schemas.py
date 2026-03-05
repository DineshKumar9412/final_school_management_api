from pydantic import BaseModel,Field
from typing import Optional
from datetime import datetime,date,time
from typing import List


class GradeCreate(BaseModel):
    start_range: float
    end_range: float
    grade: Optional[str] = Field(None, max_length=10)
   
    
class ExamCreate(BaseModel):
    exam_name: str
    school_stream_id: int
    session_yr: str
    exam_description: str
    is_active: Optional[bool] = True
    
class ExamUpdate(BaseModel):
    exam_name: Optional[str] = None
    school_stream_id: Optional[int] = None
    session_yr: Optional[str] = None
    exam_description: Optional[str] = None
    is_active: Optional[bool] = None
    
    
class ExamTimetableCreate(BaseModel):
    exam_id: int
    school_stream_id: int
    school_group_id: int
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
    
    
class ExamTimetableUpdate(BaseModel):
    exam_id: Optional[int] = None
    school_stream_id: Optional[int] = None
    school_group_id: Optional[int] = None
    subject_id: Optional[int] = None
    total_marks: Optional[float] = None
    pass_mark: Optional[float] = None
    exam_start_date: Optional[datetime] = None
    exam_end_date: Optional[datetime] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    start_ampm: Optional[str] = None
    end_ampm: Optional[str] = None
    is_active: Optional[bool] = None
    
    
    
# class StudentMarksCreate(BaseModel):
#     student_id: int
#     class_id: int
#     subject_id: int
#     grade_id: int
    
class SubjectMark(BaseModel):
    subject_id: int
    mark: float
    
class StudentMarksCreate(BaseModel):
    student_id: int
    class_id: int
    subjects: List[SubjectMark]
    
    
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