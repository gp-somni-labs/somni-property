"""
SMS Service - Twilio Integration for Agentic Text Message Responses
Handles SMS receiving via webhooks and sending
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, time
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from db.models_comms import SMSNumber, SMSMessage, SMSConversation
from core.encryption import decrypt_value, encrypt_value
import uuid

logger = logging.getLogger(__name__)


class SMSService:
    """
    SMS sending and receiving service with Twilio
    """

    def __init__(self, sms_number: SMSNumber, db: AsyncSession):
        self.sms_number = sms_number
        self.db = db
        self.twilio_client = None

    def _get_twilio_client(self) -> Client:
        """Get authenticated Twilio client"""
        if not self.twilio_client:
            auth_token = decrypt_value(self.sms_number.auth_token_encrypted)
            self.twilio_client = Client(
                self.sms_number.account_sid,
                auth_token
            )
        return self.twilio_client

    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours"""
        if not self.sms_number.business_hours_only:
            return True

        now = datetime.now().time()
        start = self.sms_number.business_hours_start
        end = self.sms_number.business_hours_end

        # Check if today is a business day
        today_weekday = datetime.now().isoweekday()  # 1=Monday, 7=Sunday
        business_days = [int(d) for d in self.sms_number.business_days.split(',')]

        if today_weekday not in business_days:
            return False

        return start <= now <= end

    async def process_incoming_sms(
        self,
        from_number: str,
        to_number: str,
        message_body: str,
        provider_message_sid: str,
        media_urls: Optional[List[str]] = None
    ) -> SMSMessage:
        """
        Process incoming SMS message from webhook
        """
        try:
            # Create SMS message record
            sms_message = SMSMessage(
                sms_number_id=self.sms_number.id,
                direction='incoming',
                from_number=from_number,
                to_number=to_number,
                message_body=message_body,
                message_length=len(message_body),
                has_media=bool(media_urls),
                media_count=len(media_urls) if media_urls else 0,
                media_urls=media_urls if media_urls else None,
                provider_message_sid=provider_message_sid,
                provider_status='received',
                received_at=datetime.utcnow()
            )

            self.db.add(sms_message)

            # Update SMS number stats
            self.sms_number.last_message_received = datetime.utcnow()
            self.sms_number.total_messages_received += 1

            await self.db.commit()
            await self.db.refresh(sms_message)

            logger.info(f"Received SMS from {from_number}: {message_body[:50]}...")

            return sms_message

        except Exception as e:
            logger.error(f"Error processing incoming SMS: {e}")
            raise

    async def send_sms(
        self,
        to_number: str,
        message_body: str,
        media_urls: Optional[List[str]] = None,
        in_reply_to_sid: Optional[str] = None
    ) -> bool:
        """
        Send SMS via Twilio
        """
        try:
            client = self._get_twilio_client()

            # Truncate message if too long (160 chars for single SMS)
            if len(message_body) > 1600:  # Max 10 SMS segments
                message_body = message_body[:1597] + "..."

            # Send message
            message_kwargs = {
                'from_': self.sms_number.phone_number,
                'to': to_number,
                'body': message_body
            }

            if media_urls:
                message_kwargs['media_url'] = media_urls

            message = client.messages.create(**message_kwargs)

            # Save sent message to database
            sent_message = SMSMessage(
                sms_number_id=self.sms_number.id,
                direction='outgoing',
                from_number=self.sms_number.phone_number,
                to_number=to_number,
                message_body=message_body,
                message_length=len(message_body),
                has_media=bool(media_urls),
                media_count=len(media_urls) if media_urls else 0,
                media_urls=media_urls if media_urls else None,
                provider_message_sid=message.sid,
                provider_status=message.status,
                received_at=datetime.utcnow(),
                ai_processed=True,
                ai_auto_replied=True
            )

            self.db.add(sent_message)

            # Update SMS number stats
            self.sms_number.last_message_sent = datetime.utcnow()
            self.sms_number.total_messages_sent += 1

            await self.db.commit()

            logger.info(f"Sent SMS to {to_number}: {message_body[:50]}...")
            return True

        except TwilioRestException as e:
            logger.error(f"Twilio error sending SMS: {e}")
            return False
        except Exception as e:
            logger.error(f"Error sending SMS: {e}")
            return False

    async def send_auto_reply(
        self,
        to_number: str,
        response_text: str,
        original_message_id: uuid.UUID
    ) -> bool:
        """
        Send automated AI response to incoming message
        """
        # Check business hours if configured
        if self.sms_number.business_hours_only and not self._is_business_hours():
            # Send out-of-hours message
            response_text = (
                f"Thank you for your message. Our office hours are "
                f"{self.sms_number.business_hours_start.strftime('%I:%M %p')} - "
                f"{self.sms_number.business_hours_end.strftime('%I:%M %p')}. "
                f"We'll respond during business hours."
            )

        success = await self.send_sms(to_number, response_text)

        if success:
            # Update original message
            query = select(SMSMessage).where(SMSMessage.id == original_message_id)
            result = await self.db.execute(query)
            original_message = result.scalar_one_or_none()

            if original_message:
                original_message.ai_auto_replied = True
                self.sms_number.total_auto_replies += 1
                await self.db.commit()

        return success

    async def get_conversation(self, contact_number: str) -> Optional[SMSConversation]:
        """Get or create SMS conversation"""
        query = select(SMSConversation).where(
            SMSConversation.sms_number_id == self.sms_number.id,
            SMSConversation.contact_number == contact_number
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            conversation = SMSConversation(
                sms_number_id=self.sms_number.id,
                contact_number=contact_number,
                first_message_at=datetime.utcnow(),
                last_message_at=datetime.utcnow()
            )
            self.db.add(conversation)
            await self.db.commit()
            await self.db.refresh(conversation)

        return conversation

    async def get_conversation_history(
        self,
        contact_number: str,
        limit: int = 10
    ) -> List[SMSMessage]:
        """Get recent message history for a contact"""
        query = select(SMSMessage).where(
            SMSMessage.sms_number_id == self.sms_number.id,
            (SMSMessage.from_number == contact_number) | (SMSMessage.to_number == contact_number)
        ).order_by(SMSMessage.received_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(reversed(result.scalars().all()))

    async def escalate_to_human(self, sms_message: SMSMessage, note: str = ""):
        """Escalate SMS to human via email or notification"""
        # TODO: Send notification to property manager
        # Could use Gotify, NTFY, or send email alert

        sms_message.escalated_to_human = True
        sms_message.escalated_at = datetime.utcnow()
        await self.db.commit()

        logger.info(f"Escalated SMS from {sms_message.from_number} to human: {note}")

        # Send auto-reply to user
        await self.send_sms(
            to_number=sms_message.from_number,
            message_body="Your message has been forwarded to our team. Someone will respond shortly."
        )


class TwilioWebhookHandler:
    """
    Handler for Twilio webhook requests
    Processes incoming SMS messages
    """

    @staticmethod
    async def handle_incoming_sms(
        webhook_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process incoming SMS webhook from Twilio

        Expected webhook_data fields:
        - MessageSid: Twilio message ID
        - From: Sender phone number
        - To: Recipient phone number (our number)
        - Body: Message text
        - NumMedia: Number of media attachments
        - MediaUrl0, MediaUrl1, etc.: URLs to media files
        """
        try:
            from_number = webhook_data.get('From')
            to_number = webhook_data.get('To')
            message_body = webhook_data.get('Body', '')
            message_sid = webhook_data.get('MessageSid')
            num_media = int(webhook_data.get('NumMedia', 0))

            # Extract media URLs
            media_urls = []
            for i in range(num_media):
                media_url = webhook_data.get(f'MediaUrl{i}')
                if media_url:
                    media_urls.append(media_url)

            # Find SMS number
            query = select(SMSNumber).where(
                SMSNumber.phone_number == to_number,
                SMSNumber.is_active == True
            )
            result = await db.execute(query)
            sms_number = result.scalar_one_or_none()

            if not sms_number:
                logger.error(f"No active SMS number found for {to_number}")
                return {
                    'success': False,
                    'error': 'Number not configured'
                }

            # Process incoming message
            service = SMSService(sms_number, db)
            sms_message = await service.process_incoming_sms(
                from_number=from_number,
                to_number=to_number,
                message_body=message_body,
                provider_message_sid=message_sid,
                media_urls=media_urls if media_urls else None
            )

            # Trigger AI processing if enabled
            if sms_number.ai_agent_enabled:
                from services.agentic_responder import agentic_responder
                asyncio.create_task(
                    agentic_responder.process_sms(sms_message, db)
                )

            return {
                'success': True,
                'message_id': str(sms_message.id)
            }

        except Exception as e:
            logger.error(f"Error handling SMS webhook: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    async def handle_status_callback(
        webhook_data: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process delivery status callback from Twilio

        Expected fields:
        - MessageSid: Twilio message ID
        - MessageStatus: sent, delivered, failed, etc.
        - ErrorCode: Error code if failed
        """
        try:
            message_sid = webhook_data.get('MessageSid')
            message_status = webhook_data.get('MessageStatus')
            error_code = webhook_data.get('ErrorCode')

            # Update message status
            query = select(SMSMessage).where(
                SMSMessage.provider_message_sid == message_sid
            )
            result = await db.execute(query)
            sms_message = result.scalar_one_or_none()

            if sms_message:
                sms_message.provider_status = message_status
                if error_code:
                    sms_message.provider_error_code = error_code
                await db.commit()

                logger.info(f"Updated SMS {message_sid} status to {message_status}")

            return {'success': True}

        except Exception as e:
            logger.error(f"Error handling status callback: {e}")
            return {'success': False, 'error': str(e)}


# Helper functions

async def send_sms_to_tenant(
    tenant_id: uuid.UUID,
    message_body: str,
    db: AsyncSession
) -> bool:
    """
    Send SMS to a specific tenant using their property's SMS number
    """
    try:
        # Get tenant and their unit/property info
        from db.models import Tenant
        query = select(Tenant).where(Tenant.id == tenant_id)
        result = await db.execute(query)
        tenant = result.scalar_one_or_none()

        if not tenant or not tenant.phone:
            logger.error(f"Tenant {tenant_id} not found or has no phone")
            return False

        # Get active SMS number for tenant's property
        # (This assumes tenant is linked to a unit/property)
        # You'll need to adjust based on your tenant-property relationship

        # For now, get first active SMS number
        query = select(SMSNumber).where(SMSNumber.is_active == True).limit(1)
        result = await db.execute(query)
        sms_number = result.scalar_one_or_none()

        if not sms_number:
            logger.error("No active SMS numbers configured")
            return False

        service = SMSService(sms_number, db)
        return await service.send_sms(
            to_number=tenant.phone,
            message_body=message_body
        )

    except Exception as e:
        logger.error(f"Error sending SMS to tenant: {e}")
        return False


async def send_sms_to_contractor(
    contractor_id: uuid.UUID,
    message_body: str,
    db: AsyncSession
) -> bool:
    """
    Send SMS to a contractor
    """
    try:
        from db.models import ServiceContractor
        query = select(ServiceContractor).where(ServiceContractor.id == contractor_id)
        result = await db.execute(query)
        contractor = result.scalar_one_or_none()

        if not contractor or not contractor.phone:
            logger.error(f"Contractor {contractor_id} not found or has no phone")
            return False

        # Get first active SMS number
        query = select(SMSNumber).where(SMSNumber.is_active == True).limit(1)
        result = await db.execute(query)
        sms_number = result.scalar_one_or_none()

        if not sms_number:
            logger.error("No active SMS numbers configured")
            return False

        service = SMSService(sms_number, db)
        return await service.send_sms(
            to_number=contractor.phone,
            message_body=message_body
        )

    except Exception as e:
        logger.error(f"Error sending SMS to contractor: {e}")
        return False
