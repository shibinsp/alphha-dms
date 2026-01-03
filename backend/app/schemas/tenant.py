from datetime import datetime, date
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    subdomain: str = Field(..., min_length=2, max_length=100, pattern="^[a-z0-9-]+$")
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")


class TenantCreate(TenantBase):
    license_key: str
    license_expires: Optional[date] = None
    config: Dict[str, Any] = {}


class TenantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    logo_url: Optional[str] = None
    primary_color: Optional[str] = Field(None, pattern="^#[0-9A-Fa-f]{6}$")
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    license_expires: Optional[date] = None


class TenantResponse(TenantBase):
    id: str
    config: Dict[str, Any]
    license_expires: Optional[date]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantConfigResponse(BaseModel):
    """Minimal tenant config for public access."""
    name: str
    logo_url: Optional[str]
    primary_color: str

    class Config:
        from_attributes = True
