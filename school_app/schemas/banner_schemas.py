# banner_schemas.py
from pydantic import BaseModel, Field
from typing import Optional


class SchoolBannerCreate(BaseModel):
    school_id: int
    bannerlink: str = Field(..., max_length=500)
    status: Optional[int] = Field(1, description="1 = active, 0 = inactive")


class SchoolBannerUpdate(BaseModel):
    bannerlink: Optional[str] = Field(None, max_length=500)
    status: Optional[int] = Field(None, description="1 = active, 0 = inactive")
