# admin_api schemas
from pydantic import BaseModel, EmailStr, ConfigDict,field_validator,Field
from typing import Optional, List, Any, Dict, Union
from datetime import datetime, date,time
from enum import Enum
from decimal import Decimal

class ResultResponse(BaseModel):
    code: int
    status:str
    message: str
    result: Optional[Dict[str, Any]] = None

class SchoolGroupCreate(BaseModel):
    school_id: int
    group_name: str = Field(..., max_length=200)
    status: Optional[str] = "Active"
    
# SchoolStream Schemas
class SchoolStreamCreate(BaseModel):
    school_id: int
    school_group_id: int
    stream_name: str
    stream_code: str
    status: Optional[str] = "Active"

# SchoolStreamClass Schemas
class SchoolStreamClassCreate(BaseModel):
    school_id: int
    school_stream_id: int
    class_name: str
    class_code: Optional[str] = None
    status: Optional[str] = "running"

# SchoolStreamSubject Schemas
class SchoolStreamSubjectCreate(BaseModel):
    school_stream_id: int
    subject_name: str
    description: Optional[str]
    status: Optional[str] = "active"
    sort_order: Optional[int] = 1