"""
Users Model - Pydantic model for user data.
"""
from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


class UsersModel(BaseModel):
    """User model for MongoDB persistence."""
    user_id: str
    name: str
    email: EmailStr
    google_id: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    picture: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator('email', mode='before')
    @classmethod
    def normalize_email(cls, v):
        if isinstance(v, str):
            return v.strip().lower()
        return v