from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.sharing import AccessRequestStatus, RequestedPermission, PermissionLevel


class AccessRequestCreate(BaseModel):
    document_id: str
    requested_permission: RequestedPermission
    reason: Optional[str] = None


class AccessRequestResponse(BaseModel):
    granted_permission: Optional[PermissionLevel] = None
    comment: Optional[str] = None


class AccessRequestAskReason(BaseModel):
    comment: str


class AccessRequestUpdate(BaseModel):
    reason: Optional[str] = None


class UserBrief(BaseModel):
    id: str
    full_name: str
    email: str

    class Config:
        from_attributes = True


class DocumentBrief(BaseModel):
    id: str
    title: str
    file_name: str

    class Config:
        from_attributes = True


class AccessRequestOut(BaseModel):
    id: str
    document_id: str
    document: Optional[DocumentBrief] = None
    requester_id: str
    requester: Optional[UserBrief] = None
    requested_permission: RequestedPermission
    reason: Optional[str] = None
    status: AccessRequestStatus
    owner_id: str
    owner: Optional[UserBrief] = None
    granted_permission: Optional[PermissionLevel] = None
    owner_comment: Optional[str] = None
    responded_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
