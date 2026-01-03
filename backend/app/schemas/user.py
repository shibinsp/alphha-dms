from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    type: str
    exp: datetime
    iat: datetime


# User schemas
class UserBase(BaseModel):
    email: str  # Use str to allow .local domains for development
    full_name: str = Field(..., min_length=2, max_length=255)
    department: Optional[str] = None
    region: Optional[str] = None
    clearance_level: str = "PUBLIC"
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role_ids: List[str] = []


class UserUpdate(BaseModel):
    email: Optional[str] = None  # Use str to allow .local domains
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    department: Optional[str] = None
    region: Optional[str] = None
    clearance_level: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    role_ids: Optional[List[str]] = None


class UserLogin(BaseModel):
    email: str  # Use str to allow .local domains for development
    password: str
    mfa_code: Optional[str] = None


class UserResponse(UserBase):
    id: str
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    last_login: Optional[datetime]
    tenant_id: str
    created_at: datetime
    updated_at: datetime
    roles: List["RoleResponse"] = []

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


# Role schemas
class RoleBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: List[str] = []


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(RoleBase):
    id: str
    is_system_role: bool
    tenant_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# MFA schemas
class MFASetupResponse(BaseModel):
    secret: str
    qr_code: str  # Base64 encoded QR code image


class MFAVerifyRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    secret: Optional[str] = None  # Used during MFA setup verification


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseModel):
    email: EmailStr


# Update forward references
UserResponse.model_rebuild()
