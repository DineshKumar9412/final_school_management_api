from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DeviceRegisterRequest(BaseModel):
    device_id:   str            = Field(..., max_length=128, description="Unique device identifier")
    os:          str            = Field(..., max_length=20,  description="e.g. android / ios")
    os_version:  Optional[str]  = Field(None, max_length=20)
    make:        Optional[str]  = Field(None, max_length=50, description="e.g. Samsung")
    model:       Optional[str]  = Field(None, max_length=50, description="e.g. Galaxy S23")
    app_version: Optional[str]  = Field(None, max_length=20)
    fcm_token:   Optional[str]  = Field(None, max_length=255)

    model_config = {
        "json_schema_extra": {
            "example": {
                "device_id":   "ANDROID-IMEI-XYZ123",
                "os":          "android",
                "os_version":  "13",
                "make":        "Samsung",
                "model":       "Galaxy S23",
                "app_version": "2.1.0",
                "fcm_token":   "fcm-token-abc123"
            }
        }
    }

class SignIN(BaseModel):
    identifier: str = Field(..., max_length=128)
    otp:        str = Field(None, min_length=6, max_length=6)
    resend:     bool = False

class ChooseAccountRequest(BaseModel):
    inq_id: int
    role:   str = Field(..., pattern="^(student|teacher|admin|staff|instructor)$")
    id:   str = Field(..., description="student_roll_id or employee_id")

class ForceLogoutRequest(BaseModel):
    identifier: str = Field(..., max_length=128, description="Phone number used to sign in")