import logging
from datetime import datetime, timedelta
from typing import Optional, List

from app.tasks import celery_app
from app.core.database import SessionLocal
from app.models.document import Document
from app.models.user import User
from app.services.email_service import get_email_service

logger = logging.getLogger(__name__)


@celery_app.task
def send_expiry_notifications() -> dict:
    """
    Send notifications for documents nearing retention expiry.
    """
    db = SessionLocal()
    email_service = get_email_service()

    try:
        # Find documents expiring in next 30 days
        expiry_threshold = datetime.utcnow() + timedelta(days=30)

        documents = db.query(Document).filter(
            Document.retention_expiry.isnot(None),
            Document.retention_expiry <= expiry_threshold,
            Document.retention_expiry > datetime.utcnow(),
            Document.is_worm_locked == True
        ).all()

        notified_count = 0
        email_count = 0

        for doc in documents:
            logger.info(
                f"Document {doc.id} ({doc.title}) expires on {doc.retention_expiry}"
            )
            notified_count += 1

            # Get document owner email
            owner = db.query(User).filter(User.id == doc.created_by).first()
            if owner and owner.email:
                # Determine action based on retention policy
                action = "ARCHIVE"
                if hasattr(doc, 'retention_policy') and doc.retention_policy:
                    action = doc.retention_policy.action if hasattr(doc.retention_policy, 'action') else "ARCHIVE"

                success = email_service.send_retention_warning(
                    to_email=owner.email,
                    document_title=doc.title,
                    retention_date=doc.retention_expiry.strftime("%B %d, %Y"),
                    action=action,
                    document_url=f"/documents/{doc.id}"
                )
                if success:
                    email_count += 1

        return {
            "status": "success",
            "documents_notified": notified_count,
            "emails_sent": email_count
        }

    finally:
        db.close()


@celery_app.task
def send_approval_notification(
    user_id: str,
    document_id: str,
    action: str,
    requester_name: Optional[str] = None,
    due_date: Optional[str] = None
) -> dict:
    """
    Send notification for approval workflow action.
    """
    db = SessionLocal()
    email_service = get_email_service()

    try:
        # Get user email
        user = db.query(User).filter(User.id == user_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()

        if not user or not document:
            logger.warning(f"User or document not found: user={user_id}, doc={document_id}")
            return {"status": "error", "message": "User or document not found"}

        email_sent = False

        if action == "REQUESTED" and user.email:
            email_sent = email_service.send_approval_requested(
                to_email=user.email,
                document_title=document.title,
                requester=requester_name or "A colleague",
                due_date=due_date,
                approval_url=f"/documents/{document_id}"
            )
        elif action == "APPROVED" and user.email:
            email_sent = email_service.send_document_approved(
                to_email=user.email,
                document_title=document.title,
                approver=requester_name or "An approver",
                document_url=f"/documents/{document_id}"
            )

        logger.info(
            f"Approval notification: User {user_id}, Document {document_id}, Action {action}, Email: {email_sent}"
        )
        return {"status": "success", "email_sent": email_sent}

    finally:
        db.close()


@celery_app.task
def send_share_notification(
    recipient_id: str,
    document_id: str,
    shared_by: str,
    permission_level: str = "VIEWER"
) -> dict:
    """
    Send notification when document is shared.
    """
    db = SessionLocal()
    email_service = get_email_service()

    try:
        # Get recipient email
        recipient = db.query(User).filter(User.id == recipient_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()
        sharer = db.query(User).filter(User.id == shared_by).first()

        if not recipient or not document:
            logger.warning(f"Recipient or document not found: recipient={recipient_id}, doc={document_id}")
            return {"status": "error", "message": "Recipient or document not found"}

        email_sent = False
        if recipient.email:
            sharer_name = f"{sharer.first_name} {sharer.last_name}" if sharer else "Someone"
            email_sent = email_service.send_document_shared(
                to_email=recipient.email,
                document_title=document.title,
                shared_by=sharer_name,
                permission_level=permission_level,
                document_url=f"/documents/{document_id}"
            )

        logger.info(
            f"Share notification: To {recipient_id}, Document {document_id}, From {shared_by}, Email: {email_sent}"
        )
        return {"status": "success", "email_sent": email_sent}

    finally:
        db.close()


@celery_app.task
def send_pii_alert(
    user_id: str,
    document_id: str,
    pii_types: List[str],
    classification: str
) -> dict:
    """
    Send PII detection alert notification.
    """
    db = SessionLocal()
    email_service = get_email_service()

    try:
        user = db.query(User).filter(User.id == user_id).first()
        document = db.query(Document).filter(Document.id == document_id).first()

        if not user or not document:
            return {"status": "error", "message": "User or document not found"}

        email_sent = False
        if user.email:
            email_sent = email_service.send_pii_detected(
                to_email=user.email,
                document_title=document.title,
                pii_types=pii_types,
                classification=classification,
                document_url=f"/documents/{document_id}"
            )

        logger.info(
            f"PII alert: User {user_id}, Document {document_id}, Types: {pii_types}, Email: {email_sent}"
        )
        return {"status": "success", "email_sent": email_sent}

    finally:
        db.close()


@celery_app.task
def send_email_notification(
    to_email: str,
    subject: str,
    template_name: str,
    context: dict
) -> dict:
    """
    Generic email notification task.

    Args:
        to_email: Recipient email
        subject: Email subject
        template_name: Template file name
        context: Template context variables
    """
    email_service = get_email_service()

    try:
        success = email_service.send_template_email(
            to_email=to_email,
            template_name=template_name,
            context=context,
            subject=subject
        )

        logger.info(f"Email notification to {to_email}: {'sent' if success else 'failed'}")
        return {"status": "success" if success else "failed", "email": to_email}

    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return {"status": "error", "message": str(e)}
