"""Notification schemas for M19"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.notifications import NotificationType, NotificationChannel, NotificationPriority


class NotificationBase(BaseModel):
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str
    message: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    action_url: Optional[str] = None
    extra_data: Dict[str, Any] = Field(default_factory=dict)


class NotificationCreate(NotificationBase):
    user_id: str


class NotificationResponse(NotificationBase):
    id: str
    tenant_id: str
    user_id: str
    is_read: bool
    read_at: Optional[datetime]
    channels_sent: List[str]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int


class NotificationPreferenceBase(BaseModel):
    notification_type: NotificationType
    in_app_enabled: bool = True
    email_enabled: bool = True
    push_enabled: bool = False
    email_digest: str = "immediate"


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    email_digest: Optional[str] = None


class NotificationPreferenceResponse(NotificationPreferenceBase):
    id: str
    tenant_id: str
    user_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BulkPreferenceUpdate(BaseModel):
    preferences: List[NotificationPreferenceUpdate]


class PushSubscriptionCreate(BaseModel):
    endpoint: str
    p256dh_key: str
    auth_key: str
    device_name: Optional[str] = None


class PushSubscriptionResponse(BaseModel):
    id: str
    device_name: Optional[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime

    class Config:
        from_attributes = True


class NotificationTemplateBase(BaseModel):
    notification_type: NotificationType
    channel: NotificationChannel
    title_template: str
    body_template: str
    subject_template: Optional[str] = None
    html_template: Optional[str] = None


class NotificationTemplateCreate(NotificationTemplateBase):
    pass


class NotificationTemplateUpdate(BaseModel):
    title_template: Optional[str] = None
    body_template: Optional[str] = None
    subject_template: Optional[str] = None
    html_template: Optional[str] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(NotificationTemplateBase):
    id: str
    tenant_id: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
