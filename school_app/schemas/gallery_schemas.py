# gallery_schemas.py
from pydantic import BaseModel, Field
from typing import Optional


class SchoolGalleryCreate(BaseModel):
    school_id: int
    bannerlink: str = Field(..., max_length=500)
    status: Optional[int] = Field(1, description="1 = active, 0 = inactive")


class SchoolGalleryUpdate(BaseModel):
    bannerlink: Optional[str] = Field(None, max_length=500)
    status: Optional[int] = Field(None, description="1 = active, 0 = inactive")
