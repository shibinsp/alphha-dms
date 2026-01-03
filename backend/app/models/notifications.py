"""Notification models for M19 - Notifications & Alerts"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Boolean,
    Enum,
    Index,
    Integer,
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base


class NotificationType(str, enum.Enum):
    # Document events
    DOCUMENT_SHARED = "document_shared"
    DOCUMENT_COMMENTED = "document_commented"
    DOCUMENT_APPROVED = "document_approved"
    DOCUMENT_REJECTED = "document_rejected"
    DOCUMENT_EXPIRING = "document_expiring"

    # Workflow events
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_REMINDER = "approval_reminder"
    WORKFLOW_COMPLETED = "workflow_completed"

    # System events
    PII_DETECTED = "pii_detected"
    LEGAL_HOLD_APPLIED = "legal_hold_applied"
    RETENTION_WARNING = "retention_warning"

    # User events
    MENTION = "mention"
    TASK_ASSIGNED = "task_assigned"

    # General
    SYSTEM_ANNOUNCEMENT = "system_announcement"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"


class NotificationPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Notification(Base):
    """User notifications"""
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    notification_type = Column(Enum(NotificationType), nullable=False)
    priority = Column(Enum(NotificationPriority), default=NotificationPriority.NORMAL)

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Related entity
    entity_type = Column(String(50), nullable=True)  # document, workflow, user
    entity_id = Column(String(36), nullable=True)

    # Action link
    action_url = Column(String(500), nullable=True)

    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)

    # Delivery status
    channels_sent = Column(JSON, default=list)  # ["in_app", "email"]

    # Additional data
    extra_data = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_notifications_user_unread", "user_id", "is_read"),
        Index("ix_notifications_tenant_created", "tenant_id", "created_at"),
        Index("ix_notifications_type", "notification_type"),
    )


class NotificationPreference(Base):
    """User notification preferences"""
    __tablename__ = "notification_preferences"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    notification_type = Column(Enum(NotificationType), nullable=False)

    # Channel preferences
    in_app_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=False)

    # Digest settings
    email_digest = Column(String(20), default="immediate")  # immediate, daily, weekly

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_notification_preferences_user", "user_id"),
    )


class NotificationTemplate(Base):
    """Notification templates"""
    __tablename__ = "notification_templates"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True)  # null = system default

    notification_type = Column(Enum(NotificationType), nullable=False)
    channel = Column(Enum(NotificationChannel), nullable=False)

    # Template content
    title_template = Column(String(200), nullable=False)
    body_template = Column(Text, nullable=False)

    # For email templates
    subject_template = Column(String(200), nullable=True)
    html_template = Column(Text, nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NotificationQueue(Base):
    """Queue for pending notifications"""
    __tablename__ = "notification_queue"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    notification_id = Column(String(36), ForeignKey("notifications.id"), nullable=False)

    channel = Column(Enum(NotificationChannel), nullable=False)
    status = Column(String(20), default="pending")  # pending, processing, sent, failed

    # Delivery tracking
    attempts = Column(Integer, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    error_message = Column(Text, nullable=True)

    # Schedule
    scheduled_for = Column(DateTime, default=datetime.utcnow)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    notification = relationship("Notification", foreign_keys=[notification_id])

    __table_args__ = (
        Index("ix_notification_queue_status", "status", "scheduled_for"),
    )


class PushSubscription(Base):
    """Web push subscriptions"""
    __tablename__ = "push_subscriptions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Push subscription data
    endpoint = Column(Text, nullable=False)
    p256dh_key = Column(String(500), nullable=False)
    auth_key = Column(String(500), nullable=False)

    # Device info
    user_agent = Column(String(500), nullable=True)
    device_name = Column(String(200), nullable=True)

    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_push_subscriptions_user", "user_id"),
    )
