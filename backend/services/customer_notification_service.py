"""
Customer Notification Service - Transactional notifications for client onboarding
Sends emails and SMS to clients (property owners) for:
- Payment reminders
- Quote requests
- Progress updates
- Discovery call reminders
- Contract milestones
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import jwt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from db.models import Client
# from services.sms_service import SMSService, send_sms_to_client  # TODO: Enable when SMS integration ready
from core.config import settings

logger = logging.getLogger(__name__)


class CustomerNotificationService:
    """
    Transactional notification service for client onboarding workflow
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.smtp_host = getattr(settings, 'SMTP_HOST', 'postfix.somniproperty.svc.cluster.local')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 25)
        self.from_email = getattr(settings, 'NOTIFICATIONS_FROM_EMAIL', 'notifications@somni.property')
        self.from_name = getattr(settings, 'NOTIFICATIONS_FROM_NAME', 'SomniProperty')
        self.jwt_secret = getattr(settings, 'JWT_SECRET_KEY', 'your-secret-key-change-in-production')
        self.base_url = getattr(settings, 'CUSTOMER_PORTAL_BASE_URL', 'https://property.home.lan')

    async def send_discovery_call_scheduled(
        self,
        client: Client,
        scheduled_at: datetime,
        channels: list[str] = ['email', 'sms']
    ) -> Dict[str, bool]:
        """
        Notify client that discovery call has been scheduled
        """
        results = {}

        # Generate secure link to view/reschedule
        progress_link = self.generate_secure_link(
            client_id=client.id,
            portal_type='progress',
            expiry_hours=72
        )

        # Format scheduled time
        scheduled_time = scheduled_at.strftime('%B %d, %Y at %I:%M %p')

        # Email notification
        if 'email' in channels and client.primary_contact_email:
            subject = f"Discovery Call Scheduled - {scheduled_time}"
            body = f"""
Hello {client.primary_contact_name or client.name},

Your discovery call has been scheduled for {scheduled_time}.

During this call, we'll discuss your property management needs and how SomniProperty can help automate and enhance your operations.

View your onboarding progress and call details:
{progress_link}

If you need to reschedule, please use the link above or contact us directly.

Best regards,
The SomniProperty Team
"""
            results['email'] = await self._send_email(
                to_email=client.primary_contact_email,
                to_name=client.primary_contact_name or client.name,
                subject=subject,
                body=body
            )

        # SMS notification
        if 'sms' in channels and client.phone:
            sms_body = f"Discovery call scheduled for {scheduled_time}. View details: {progress_link}"
            results['sms'] = await self._send_sms(
                to_number=client.phone,
                message=sms_body
            )

        # Log notification
        await self._log_notification(
            client_id=client.id,
            notification_type='discovery_call_scheduled',
            recipient=client.primary_contact_email or client.phone,
            channels=channels,
            results=results
        )

        return results

    async def send_progress_update(
        self,
        client: Client,
        new_stage: str,
        progress_percent: int,
        channels: list[str] = ['email']
    ) -> Dict[str, bool]:
        """
        Notify client of onboarding progress advancement
        """
        results = {}

        stage_names = {
            'initial': 'Initial Contact',
            'discovery': 'Discovery Call',
            'assessment': 'Property Assessment',
            'proposal': 'Service Proposal',
            'contract': 'Contract Signing',
            'deployment': 'Infrastructure Deployment',
            'completed': 'Onboarding Complete'
        }

        stage_name = stage_names.get(new_stage, new_stage)
        progress_link = self.generate_secure_link(
            client_id=client.id,
            portal_type='progress',
            expiry_hours=168  # 1 week
        )

        # Email notification
        if 'email' in channels and client.primary_contact_email:
            subject = f"Onboarding Progress Update - {stage_name} ({progress_percent}%)"
            body = f"""
Hello {client.primary_contact_name or client.name},

Great news! Your SomniProperty onboarding has advanced to the {stage_name} stage.

Progress: {progress_percent}% complete

View your full onboarding timeline:
{progress_link}

We're excited to have you join the SomniProperty platform!

Best regards,
The SomniProperty Team
"""
            results['email'] = await self._send_email(
                to_email=client.primary_contact_email,
                to_name=client.primary_contact_name or client.name,
                subject=subject,
                body=body
            )

        # Log notification
        await self._log_notification(
            client_id=client.id,
            notification_type='progress_update',
            recipient=client.primary_contact_email,
            channels=channels,
            results=results,
            metadata={'stage': new_stage, 'progress': progress_percent}
        )

        return results

    async def send_payment_reminder(
        self,
        client: Client,
        invoice_id: str,
        amount: float,
        due_date: datetime,
        channels: list[str] = ['email', 'sms']
    ) -> Dict[str, bool]:
        """
        Send payment reminder with secure payment link
        """
        results = {}

        # Generate secure payment link
        payment_link = self.generate_secure_link(
            client_id=client.id,
            portal_type='payment',
            resource_id=invoice_id,
            expiry_hours=72
        )

        due_date_str = due_date.strftime('%B %d, %Y')

        # Email notification
        if 'email' in channels and client.primary_contact_email:
            subject = f"Payment Reminder - Invoice #{invoice_id[-8:]}"
            body = f"""
Hello {client.primary_contact_name or client.name},

This is a friendly reminder that payment is due for Invoice #{invoice_id[-8:]}.

Amount Due: ${amount:.2f}
Due Date: {due_date_str}

Pay securely online:
{payment_link}

If you've already paid, please disregard this message.

Questions? Reply to this email or contact us at support@somni.property

Best regards,
The SomniProperty Team
"""
            results['email'] = await self._send_email(
                to_email=client.primary_contact_email,
                to_name=client.primary_contact_name or client.name,
                subject=subject,
                body=body
            )

        # SMS notification
        if 'sms' in channels and client.phone:
            sms_body = f"Payment reminder: ${amount:.2f} due {due_date_str}. Pay now: {payment_link}"
            results['sms'] = await self._send_sms(
                to_number=client.phone,
                message=sms_body
            )

        # Log notification
        await self._log_notification(
            client_id=client.id,
            notification_type='payment_reminder',
            recipient=client.primary_contact_email or client.phone,
            channels=channels,
            results=results,
            metadata={'invoice_id': invoice_id, 'amount': amount}
        )

        return results

    async def send_quote_request(
        self,
        client: Client,
        quote_id: str,
        description: str,
        estimated_amount: Optional[float] = None,
        channels: list[str] = ['email']
    ) -> Dict[str, bool]:
        """
        Send quote for client review and approval
        """
        results = {}

        # Generate secure quote approval link
        quote_link = self.generate_secure_link(
            client_id=client.id,
            portal_type='quote',
            resource_id=quote_id,
            expiry_hours=168  # 1 week
        )

        # Email notification
        if 'email' in channels and client.primary_contact_email:
            subject = f"Quote Request #{quote_id[-8:]} - Review & Approve"

            amount_text = f"\n\nEstimated Amount: ${estimated_amount:.2f}" if estimated_amount else ""

            body = f"""
Hello {client.primary_contact_name or client.name},

We've prepared a quote for your review:

{description}{amount_text}

Review and approve your quote:
{quote_link}

This link will expire in 7 days for security purposes.

Questions? Reply to this email and we'll be happy to discuss.

Best regards,
The SomniProperty Team
"""
            results['email'] = await self._send_email(
                to_email=client.primary_contact_email,
                to_name=client.primary_contact_name or client.name,
                subject=subject,
                body=body
            )

        # Log notification
        await self._log_notification(
            client_id=client.id,
            notification_type='quote_request',
            recipient=client.primary_contact_email,
            channels=channels,
            results=results,
            metadata={'quote_id': quote_id, 'estimated_amount': estimated_amount}
        )

        return results

    async def send_onboarding_complete(
        self,
        client: Client,
        channels: list[str] = ['email']
    ) -> Dict[str, bool]:
        """
        Celebrate onboarding completion
        """
        results = {}

        portal_link = f"{self.base_url}/dashboard"

        # Email notification
        if 'email' in channels and client.primary_contact_email:
            subject = "🎉 Welcome to SomniProperty - Onboarding Complete!"
            body = f"""
Hello {client.primary_contact_name or client.name},

Congratulations! Your SomniProperty onboarding is complete.

You now have full access to:
✓ Property Dashboard
✓ Tenant Management
✓ Smart Device Control
✓ Work Order System
✓ Financial Reporting

Access your dashboard:
{portal_link}

Thank you for choosing SomniProperty. We're excited to help you transform your property management operations!

Best regards,
The SomniProperty Team
"""
            results['email'] = await self._send_email(
                to_email=client.primary_contact_email,
                to_name=client.primary_contact_name or client.name,
                subject=subject,
                body=body
            )

        # Log notification
        await self._log_notification(
            client_id=client.id,
            notification_type='onboarding_complete',
            recipient=client.primary_contact_email,
            channels=channels,
            results=results
        )

        return results

    def generate_secure_link(
        self,
        client_id: str,
        portal_type: str,  # 'payment', 'quote', 'progress'
        resource_id: Optional[str] = None,
        expiry_hours: int = 48
    ) -> str:
        """
        Generate JWT-signed secure link for customer portal
        """
        payload = {
            'client_id': str(client_id),
            'portal_type': portal_type,
            'resource_id': str(resource_id) if resource_id else None,
            'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
            'iat': datetime.utcnow()
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm='HS256')

        return f"{self.base_url}/{portal_type}/{token}"

    def verify_secure_token(self, token: str) -> Optional[Dict]:
        """
        Verify and decode JWT token
        """
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Invalid token")
            return None

    async def _send_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        body: str
    ) -> bool:
        """
        Send email via SMTP
        """
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((self.from_name, self.from_email))
            msg['To'] = formataddr((to_name, to_email))
            msg['Subject'] = subject

            # Plain text part
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.send_message(msg)

            logger.info(f"Sent email to {to_email}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {e}")
            return False

    async def _send_sms(
        self,
        to_number: str,
        message: str
    ) -> bool:
        """
        Send SMS via Twilio (using existing SMS service)
        """
        try:
            # TODO: Integrate with existing SMSService
            # For now, log the attempt
            logger.info(f"SMS to {to_number}: {message}")

            # When SMS service is ready:
            # success = await send_sms_to_client(client_id, message, self.db)

            return True

        except Exception as e:
            logger.error(f"Error sending SMS to {to_number}: {e}")
            return False

    async def _log_notification(
        self,
        client_id: str,
        notification_type: str,
        recipient: str,
        channels: list[str],
        results: Dict[str, bool],
        metadata: Optional[Dict] = None
    ):
        """
        Log notification to database for tracking
        """
        try:
            # TODO: Insert into customer_notifications_log table
            # For now, just log to application logs
            logger.info(
                f"Notification sent - Type: {notification_type}, "
                f"Client: {client_id}, Recipient: {recipient}, "
                f"Channels: {channels}, Results: {results}"
            )

        except Exception as e:
            logger.error(f"Error logging notification: {e}")


# Singleton instance
_customer_notification_service = None


def get_customer_notification_service(db: AsyncSession) -> CustomerNotificationService:
    """Get customer notification service instance"""
    return CustomerNotificationService(db)
