# schemas/user.py
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserRead(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True

class UserCreate(BaseModel):
    name: str
    subject: Optional[str] = None
    email: Optional[EmailStr] = None