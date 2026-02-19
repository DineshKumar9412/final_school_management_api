from pydantic import BaseModel, EmailStr, ConfigDict,field_validator,Field
from typing import Optional, List, Any, Dict, Union
from datetime import datetime, date,time
from enum import Enum
from decimal import Decimal




class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"

class StudentInquiryCreate(BaseModel):
    student_name: str
    gender: Optional[GenderEnum] = None
    age: Optional[int] = None
    class_id: Optional[int] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_occupation: Optional[str] = None
    guardian_gender: Optional[GenderEnum] = None
    
    
class StudentCreate(BaseModel):
    class_id : int
    section_id: int
    student_inq_id: Optional[int] = None
    first_name: str
    last_name: str
    gender: str
    dob: date
    age: Optional[int] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[str] = None
    guardian_first_name: Optional[str] = None
    guardian_last_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    guardian_email: Optional[str] = None
    guardian_gender: Optional[str] = None
    enroll_date : Optional[datetime] = None
    status: Optional[str] = "active"