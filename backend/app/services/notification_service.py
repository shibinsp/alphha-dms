"""Notification service for M19 - Notifications & Alerts"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.models.notifications import (
    Notification, NotificationPreference, NotificationTemplate,
    NotificationQueue, PushSubscription,
    NotificationType, NotificationChannel, NotificationPriority
)
from app.schemas.notifications import (
    NotificationCreate, NotificationPreferenceUpdate,
    PushSubscriptionCreate, NotificationTemplateCreate
)


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create_notification(
        self,
        tenant_id: str,
        user_id: str,
        notification_type: NotificationType,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        entity_type: str = None,
        entity_id: str = None,
        action_url: str = None,
        metadata: Dict = None
    ) -> Notification:
        """Create a notification for a user"""
        notification = Notification(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=notification_type,
            priority=priority,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            action_url=action_url,
            extra_data=metadata or {},
            channels_sent=["in_app"]
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)

        # Queue for other channels based on preferences
        self._queue_notification_delivery(notification)

        return notification

    def _queue_notification_delivery(self, notification: Notification):
        """Queue notification for delivery via enabled channels"""
        # Get user preferences
        preferences = self.db.query(NotificationPreference).filter(
            NotificationPreference.user_id == notification.user_id,
            NotificationPreference.notification_type == notification.notification_type
        ).first()

        if not preferences:
            # Use defaults
            return

        if preferences.email_enabled:
            self._queue_for_channel(notification, NotificationChannel.EMAIL)

        if preferences.push_enabled:
            self._queue_for_channel(notification, NotificationChannel.PUSH)

    def _queue_for_channel(self, notification: Notification, channel: NotificationChannel):
        """Add notification to delivery queue"""
        queue_item = NotificationQueue(
            id=str(uuid.uuid4()),
            notification_id=notification.id,
            channel=channel,
            status="pending"
        )
        self.db.add(queue_item)
        self.db.commit()

    def get_user_notifications(
        self,
        tenant_id: str,
        user_id: str,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50
    ) -> tuple[List[Notification], int, int]:
        """Get notifications for a user"""
        query = self.db.query(Notification).filter(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id
        )

        if unread_only:
            query = query.filter(Notification.is_read == False)

        total = query.count()
        unread_count = self.db.query(func.count(Notification.id)).filter(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            Notification.is_read == False
        ).scalar() or 0

        notifications = query.order_by(
            Notification.created_at.desc()
        ).offset(skip).limit(limit).all()

        return notifications, total, unread_count

    def mark_as_read(self, notification_id: str, user_id: str) -> Optional[Notification]:
        """Mark a notification as read"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if not notification:
            return None

        notification.is_read = True
        notification.read_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_as_read(self, tenant_id: str, user_id: str) -> int:
        """Mark all notifications as read for a user"""
        count = self.db.query(Notification).filter(
            Notification.tenant_id == tenant_id,
            Notification.user_id == user_id,
            Notification.is_read == False
        ).update({
            "is_read": True,
            "read_at": datetime.utcnow()
        })
        self.db.commit()
        return count

    def delete_notification(self, notification_id: str, user_id: str) -> bool:
        """Delete a notification"""
        notification = self.db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()

        if not notification:
            return False

        self.db.delete(notification)
        self.db.commit()
        return True

    # Preference management
    def get_user_preferences(
        self,
        tenant_id: str,
        user_id: str
    ) -> List[NotificationPreference]:
        """Get user notification preferences"""
        return self.db.query(NotificationPreference).filter(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id
        ).all()

    def update_preference(
        self,
        tenant_id: str,
        user_id: str,
        notification_type: NotificationType,
        data: NotificationPreferenceUpdate
    ) -> NotificationPreference:
        """Update or create a notification preference"""
        preference = self.db.query(NotificationPreference).filter(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type
        ).first()

        if not preference:
            preference = NotificationPreference(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                notification_type=notification_type
            )
            self.db.add(preference)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(preference, field, value)

        self.db.commit()
        self.db.refresh(preference)
        return preference

    def initialize_default_preferences(
        self,
        tenant_id: str,
        user_id: str
    ) -> List[NotificationPreference]:
        """Initialize default preferences for a new user"""
        preferences = []
        for ntype in NotificationType:
            pref = NotificationPreference(
                id=str(uuid.uuid4()),
                tenant_id=tenant_id,
                user_id=user_id,
                notification_type=ntype,
                in_app_enabled=True,
                email_enabled=True,
                push_enabled=False
            )
            self.db.add(pref)
            preferences.append(pref)

        self.db.commit()
        return preferences

    # Push subscriptions
    def register_push_subscription(
        self,
        tenant_id: str,
        user_id: str,
        data: PushSubscriptionCreate
    ) -> PushSubscription:
        """Register a web push subscription"""
        # Check for existing subscription with same endpoint
        existing = self.db.query(PushSubscription).filter(
            PushSubscription.endpoint == data.endpoint
        ).first()

        if existing:
            existing.user_id = user_id
            existing.p256dh_key = data.p256dh_key
            existing.auth_key = data.auth_key
            existing.device_name = data.device_name
            existing.is_active = True
            existing.last_used_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(existing)
            return existing

        subscription = PushSubscription(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            **data.model_dump()
        )
        self.db.add(subscription)
        self.db.commit()
        self.db.refresh(subscription)
        return subscription

    def get_user_push_subscriptions(
        self,
        user_id: str
    ) -> List[PushSubscription]:
        """Get user's push subscriptions"""
        return self.db.query(PushSubscription).filter(
            PushSubscription.user_id == user_id,
            PushSubscription.is_active == True
        ).all()

    def remove_push_subscription(
        self,
        subscription_id: str,
        user_id: str
    ) -> bool:
        """Remove a push subscription"""
        subscription = self.db.query(PushSubscription).filter(
            PushSubscription.id == subscription_id,
            PushSubscription.user_id == user_id
        ).first()

        if not subscription:
            return False

        subscription.is_active = False
        self.db.commit()
        return True

    # Helper methods for common notifications
    def notify_document_shared(
        self,
        tenant_id: str,
        user_id: str,
        document_id: str,
        document_title: str,
        shared_by: str
    ):
        """Send notification when document is shared"""
        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=NotificationType.DOCUMENT_SHARED,
            title="Document Shared",
            message=f"{shared_by} shared '{document_title}' with you",
            entity_type="document",
            entity_id=document_id,
            action_url=f"/documents/{document_id}"
        )

    def notify_approval_requested(
        self,
        tenant_id: str,
        approver_id: str,
        document_id: str,
        document_title: str,
        requester: str
    ):
        """Send notification when approval is requested"""
        return self.create_notification(
            tenant_id=tenant_id,
            user_id=approver_id,
            notification_type=NotificationType.APPROVAL_REQUESTED,
            priority=NotificationPriority.HIGH,
            title="Approval Requested",
            message=f"{requester} requested your approval for '{document_title}'",
            entity_type="document",
            entity_id=document_id,
            action_url=f"/approvals"
        )

    def notify_document_approved(
        self,
        tenant_id: str,
        user_id: str,
        document_id: str,
        document_title: str,
        approver: str
    ):
        """Send notification when document is approved"""
        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=NotificationType.DOCUMENT_APPROVED,
            title="Document Approved",
            message=f"'{document_title}' was approved by {approver}",
            entity_type="document",
            entity_id=document_id,
            action_url=f"/documents/{document_id}"
        )

    def notify_document_rejected(
        self,
        tenant_id: str,
        user_id: str,
        document_id: str,
        document_title: str,
        rejector: str,
        reason: str = None
    ):
        """Send notification when document is rejected"""
        message = f"'{document_title}' was rejected by {rejector}"
        if reason:
            message += f": {reason}"

        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=NotificationType.DOCUMENT_REJECTED,
            priority=NotificationPriority.HIGH,
            title="Document Rejected",
            message=message,
            entity_type="document",
            entity_id=document_id,
            action_url=f"/documents/{document_id}"
        )

    def notify_pii_detected(
        self,
        tenant_id: str,
        user_id: str,
        document_id: str,
        document_title: str,
        pii_types: List[str]
    ):
        """Send notification when PII is detected"""
        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=NotificationType.PII_DETECTED,
            priority=NotificationPriority.HIGH,
            title="PII Detected",
            message=f"Sensitive data ({', '.join(pii_types)}) detected in '{document_title}'",
            entity_type="document",
            entity_id=document_id,
            action_url=f"/documents/{document_id}",
            metadata={"pii_types": pii_types}
        )

    def notify_legal_hold_applied(
        self,
        tenant_id: str,
        user_id: str,
        document_id: str,
        document_title: str,
        hold_name: str
    ):
        """Send notification when legal hold is applied"""
        return self.create_notification(
            tenant_id=tenant_id,
            user_id=user_id,
            notification_type=NotificationType.LEGAL_HOLD_APPLIED,
            priority=NotificationPriority.URGENT,
            title="Legal Hold Applied",
            message=f"'{document_title}' has been placed under legal hold: {hold_name}",
            entity_type="document",
            entity_id=document_id,
            action_url=f"/compliance/legal-holds"
        )
