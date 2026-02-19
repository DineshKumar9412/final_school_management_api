

from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date,time


class RoleCreate(BaseModel):
    role_name: Optional[str] = None
    is_active: Optional[bool] = True
    
    

# ********************* Employee ******************
    
class EmployeeCreate(BaseModel):
    emp_id: Optional[int] = None
    first_name: str
    last_name: str
    DOB: date
    gender: str
    qualification:str
    mobile:str
    address: str
    email: EmailStr
    salary: Optional[float] = None
    session_yr: Optional[str] = None
    joining_dt: Optional[date] = None
    status: str
    is_active: Optional[bool] = True
    

class EmployeeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    DOB: Optional[date] = None
    gender: Optional[str] = None
    qualification: Optional[str] = None
    mobile: Optional[str] = None
    address: Optional[str] = None
    email: Optional[EmailStr] = None
    salary: Optional[float] = None
    session_yr: Optional[str] = None
    joining_dt: Optional[date] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None
    
     
class EmployeeMapping(BaseModel):
    emp_id:int
    role_id : int
    class_id: int
    subject_id: int
    emp_name:str
    
    
class GetEmployeeMapping(BaseModel):
    class_id: str
    section:str
    group:str
    
    
    
# TODO need to work 
class EmployeeRoleMapCreate(BaseModel):
    emp_id: Optional[int] = None
    role_id: Optional[int] = None
    class_id: Optional[int] = None
    subject_id: Optional[int] = None
    