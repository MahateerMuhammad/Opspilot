"""Pydantic schemas for the API."""
from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from database.models import RoleEnum

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    sub: str = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr
    role: RoleEnum
    created_at: datetime

    class Config:
        from_attributes = True
