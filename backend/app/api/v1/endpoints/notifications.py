"""Notifications API endpoints for M19"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.v1.dependencies import get_current_user, get_current_tenant
from app.models import User, Tenant
from app.models.notifications import NotificationType
from app.services.notification_service import NotificationService
from app.schemas.notifications import (
    NotificationResponse, NotificationListResponse,
    NotificationPreferenceResponse, NotificationPreferenceUpdate,
    PushSubscriptionCreate, PushSubscriptionResponse
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    unread_only: bool = Query(False, description="Only return unread notifications"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get user notifications"""
    service = NotificationService(db)
    notifications, total, unread_count = service.get_user_notifications(
        tenant.id, current_user.id, unread_only, skip, limit
    )
    return NotificationListResponse(
        items=notifications,
        total=total,
        unread_count=unread_count
    )


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get count of unread notifications"""
    service = NotificationService(db)
    _, _, unread_count = service.get_user_notifications(
        tenant.id, current_user.id, unread_only=True, limit=0
    )
    return {"unread_count": unread_count}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark a notification as read"""
    service = NotificationService(db)
    notification = service.mark_as_read(notification_id, current_user.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


@router.put("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Mark all notifications as read"""
    service = NotificationService(db)
    count = service.mark_all_as_read(tenant.id, current_user.id)
    return {"message": f"Marked {count} notifications as read"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a notification"""
    service = NotificationService(db)
    if not service.delete_notification(notification_id, current_user.id):
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"message": "Notification deleted"}


# Preferences
@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Get notification preferences"""
    service = NotificationService(db)
    preferences = service.get_user_preferences(tenant.id, current_user.id)

    # If no preferences, initialize defaults
    if not preferences:
        preferences = service.initialize_default_preferences(tenant.id, current_user.id)

    return preferences


@router.put("/preferences/{notification_type}", response_model=NotificationPreferenceResponse)
def update_preference(
    notification_type: NotificationType,
    data: NotificationPreferenceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Update a notification preference"""
    service = NotificationService(db)
    return service.update_preference(tenant.id, current_user.id, notification_type, data)


# Push subscriptions
@router.get("/push-subscriptions", response_model=List[PushSubscriptionResponse])
def get_push_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's push subscriptions"""
    service = NotificationService(db)
    return service.get_user_push_subscriptions(current_user.id)


@router.post("/push-subscriptions", response_model=PushSubscriptionResponse)
def register_push_subscription(
    data: PushSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Register a push subscription"""
    service = NotificationService(db)
    return service.register_push_subscription(tenant.id, current_user.id, data)


@router.delete("/push-subscriptions/{subscription_id}")
def remove_push_subscription(
    subscription_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove a push subscription"""
    service = NotificationService(db)
    if not service.remove_push_subscription(subscription_id, current_user.id):
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {"message": "Subscription removed"}
