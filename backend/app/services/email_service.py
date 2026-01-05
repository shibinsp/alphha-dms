"""Email Service for sending notifications via SMTP"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, List, Dict, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Template directory
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "email"


class EmailService:
    """Service for sending emails via SMTP"""

    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS
        self.use_ssl = settings.SMTP_USE_SSL

        # Initialize Jinja2 environment for templates
        if TEMPLATE_DIR.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(TEMPLATE_DIR)),
                autoescape=select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = None
            logger.warning(f"Email template directory not found: {TEMPLATE_DIR}")

    def is_configured(self) -> bool:
        """Check if SMTP is properly configured"""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password)

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        reply_to: Optional[str] = None
    ) -> bool:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body content
            text_content: Plain text body (fallback)
            cc: CC recipients
            bcc: BCC recipients
            reply_to: Reply-to address

        Returns:
            bool: True if sent successfully
        """
        if not self.is_configured():
            logger.warning("SMTP not configured, skipping email send")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = to_email

            if cc:
                msg['Cc'] = ', '.join(cc)

            if reply_to:
                msg['Reply-To'] = reply_to

            # Add plain text part
            if text_content:
                text_part = MIMEText(text_content, 'plain', 'utf-8')
                msg.attach(text_part)

            # Add HTML part
            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            # Get all recipients
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Send email
            if self.use_ssl:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, recipients, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.use_tls:
                        server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.from_email, recipients, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_template_email(
        self,
        to_email: str,
        template_name: str,
        context: Dict[str, Any],
        subject: Optional[str] = None
    ) -> bool:
        """
        Send an email using a Jinja2 template.

        Args:
            to_email: Recipient email address
            template_name: Template file name (e.g., 'notification.html')
            context: Template context variables
            subject: Email subject (can also be in context)

        Returns:
            bool: True if sent successfully
        """
        if not self.jinja_env:
            logger.error("Jinja2 environment not initialized - templates missing")
            return False

        try:
            # Load template
            template = self.jinja_env.get_template(template_name)

            # Add common context
            context.setdefault('app_name', settings.PROJECT_NAME)
            context.setdefault('app_url', 'https://alphha.io')
            context.setdefault('year', '2024')

            # Render template
            html_content = template.render(**context)

            # Get subject from context if not provided
            email_subject = subject or context.get('subject', 'Notification from Alphha DMS')

            # Generate plain text version
            text_content = self._html_to_text(html_content)

            return self.send_email(
                to_email=to_email,
                subject=email_subject,
                html_content=html_content,
                text_content=text_content
            )

        except Exception as e:
            logger.error(f"Error sending template email: {e}")
            return False

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text (basic conversion)"""
        import re
        # Remove HTML tags
        text = re.sub(r'<style.*?</style>', '', html, flags=re.DOTALL)
        text = re.sub(r'<script.*?</script>', '', text, flags=re.DOTALL)
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        return text

    # Convenience methods for common notification types

    def send_document_shared(
        self,
        to_email: str,
        document_title: str,
        shared_by: str,
        permission_level: str,
        document_url: str
    ) -> bool:
        """Send document shared notification"""
        return self.send_template_email(
            to_email=to_email,
            template_name='document_shared.html',
            context={
                'subject': f'Document Shared: {document_title}',
                'document_title': document_title,
                'shared_by': shared_by,
                'permission_level': permission_level,
                'document_url': document_url,
            }
        )

    def send_approval_requested(
        self,
        to_email: str,
        document_title: str,
        requester: str,
        due_date: Optional[str] = None,
        approval_url: str = None
    ) -> bool:
        """Send approval request notification"""
        return self.send_template_email(
            to_email=to_email,
            template_name='approval_requested.html',
            context={
                'subject': f'Approval Required: {document_title}',
                'document_title': document_title,
                'requester': requester,
                'due_date': due_date,
                'approval_url': approval_url,
            }
        )

    def send_document_approved(
        self,
        to_email: str,
        document_title: str,
        approver: str,
        comments: Optional[str] = None,
        document_url: str = None
    ) -> bool:
        """Send document approved notification"""
        return self.send_template_email(
            to_email=to_email,
            template_name='document_approved.html',
            context={
                'subject': f'Document Approved: {document_title}',
                'document_title': document_title,
                'approver': approver,
                'comments': comments,
                'document_url': document_url,
            }
        )

    def send_pii_detected(
        self,
        to_email: str,
        document_title: str,
        pii_types: List[str],
        classification: str,
        document_url: str = None
    ) -> bool:
        """Send PII detection alert"""
        return self.send_template_email(
            to_email=to_email,
            template_name='pii_detected.html',
            context={
                'subject': f'PII Detected: {document_title}',
                'document_title': document_title,
                'pii_types': pii_types,
                'classification': classification,
                'document_url': document_url,
            }
        )

    def send_retention_warning(
        self,
        to_email: str,
        document_title: str,
        retention_date: str,
        action: str,
        document_url: str = None
    ) -> bool:
        """Send retention policy warning"""
        return self.send_template_email(
            to_email=to_email,
            template_name='retention_warning.html',
            context={
                'subject': f'Retention Notice: {document_title}',
                'document_title': document_title,
                'retention_date': retention_date,
                'action': action,
                'document_url': document_url,
            }
        )

    def send_test_email(self, to_email: str) -> bool:
        """Send a test email to verify SMTP configuration"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #1890ff; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .success { color: #52c41a; font-size: 24px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Alphha DMS</h1>
                </div>
                <div class="content">
                    <p class="success">✓ SMTP Configuration Successful!</p>
                    <p>This is a test email from Alphha DMS to verify your SMTP settings are working correctly.</p>
                    <p><strong>SMTP Host:</strong> {host}</p>
                    <p><strong>SMTP Port:</strong> {port}</p>
                    <p>If you received this email, your email notifications are properly configured.</p>
                </div>
            </div>
        </body>
        </html>
        """.format(host=self.smtp_host, port=self.smtp_port)

        return self.send_email(
            to_email=to_email,
            subject='Alphha DMS - Test Email',
            html_content=html_content,
            text_content='This is a test email from Alphha DMS. Your SMTP configuration is working correctly.'
        )


# Singleton instance
_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get the email service singleton"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
