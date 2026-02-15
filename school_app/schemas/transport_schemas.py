from pydantic import BaseModel, EmailStr, ConfigDict,field_validator,Field
from typing import Optional, List, Any, Dict, Union
from datetime import datetime, date,time
from enum import Enum
from decimal import Decimal


class VehicleDetailsCreate(BaseModel):
    vehicle_no: Optional[str]
    vehicle_capacity: Optional[int]
    vehicle_reg_no: Optional[str]
    status: Optional[str]
    driver_name: str
    helper_name: str
    
class RouteCreate(BaseModel):
    name: str
    vehicle_no: Optional[str]
    distance: Optional[int]
    status: Optional[str]
    pick_start_time: time
    pick_end_time: time
    drop_start_time: time
    drop_end_time: time
    
class VehicleRouteMapCreate(BaseModel):
    route_id: int
    vehicle_id: int
    driver_name: str
    helper_name: str
    driver_mob_no: Optional[str]
    helper_mob_no: Optional[str]
    
    
class TransportationStudentCreate(BaseModel):
    vehicle_id: int
    class_id: int
    student_id: int
    group_id: int
    session_yr: Optional[str]
    
class VehicleExpenseCreate(BaseModel):
    vehicle_id: int
    session_yr: Optional[str]
    amount: Optional[Decimal]
    date: Optional[datetime]
    description: Optional[str]
    
    
