# event_schemas.py
from pydantic import BaseModel, Field
from typing import Optional


class SchoolEventCreate(BaseModel):
    school_id: int
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    status: Optional[int] = Field(1, description="1 = active, 0 = inactive")


class SchoolEventUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    status: Optional[int] = Field(None, description="1 = active, 0 = inactive")
