"""
Email Service - IMAP/SMTP Integration for Agentic Email Responses
Handles email polling, parsing, and sending
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.utils import parseaddr, formataddr
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import asyncio
import base64
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx

from db.models_comms import EmailAccount, EmailMessage, EmailThread
from core.encryption import decrypt_value, encrypt_value
import uuid

logger = logging.getLogger(__name__)


class EmailService:
    """
    Email polling and sending service with IMAP/SMTP
    """

    def __init__(self, email_account: EmailAccount, db: AsyncSession):
        self.account = email_account
        self.db = db
        self.imap_client = None
        self.smtp_client = None

    async def connect_imap(self):
        """Connect to IMAP server"""
        try:
            # Decrypt password
            password = decrypt_value(self.account.imap_password_encrypted)

            # Connect to IMAP
            if self.account.imap_use_ssl:
                self.imap_client = imaplib.IMAP4_SSL(
                    self.account.imap_host,
                    self.account.imap_port
                )
            else:
                self.imap_client = imaplib.IMAP4(
                    self.account.imap_host,
                    self.account.imap_port
                )

            # Login
            self.imap_client.login(self.account.imap_username, password)

            # Select folder
            self.imap_client.select(self.account.imap_folder)

            logger.info(f"Connected to IMAP: {self.account.email_address}")
            return True

        except Exception as e:
            logger.error(f"IMAP connection error for {self.account.email_address}: {e}")
            return False

    async def poll_new_emails(self) -> List[EmailMessage]:
        """
        Poll for new emails and return EmailMessage objects
        """
        if not self.imap_client:
            if not await self.connect_imap():
                return []

        new_messages = []

        try:
            # Search for unseen messages
            status, message_ids = self.imap_client.search(None, 'UNSEEN')

            if status != 'OK':
                logger.error(f"IMAP search failed for {self.account.email_address}")
                return []

            for msg_id in message_ids[0].split():
                try:
                    # Fetch message
                    status, msg_data = self.imap_client.fetch(msg_id, '(RFC822)')

                    if status != 'OK':
                        continue

                    # Parse email
                    email_msg = email.message_from_bytes(msg_data[0][1])
                    email_message = await self._parse_email(email_msg)

                    if email_message:
                        new_messages.append(email_message)
                        logger.info(f"Polled email: {email_message.subject} from {email_message.from_address}")

                except Exception as e:
                    logger.error(f"Error parsing email {msg_id}: {e}")
                    continue

            # Update account last_checked
            self.account.last_checked = datetime.utcnow()
            self.account.total_emails_processed += len(new_messages)
            await self.db.commit()

        except Exception as e:
            logger.error(f"Error polling emails: {e}")

        return new_messages

    async def _parse_email(self, email_msg: email.message.Message) -> Optional[EmailMessage]:
        """
        Parse raw email message into EmailMessage model
        """
        try:
            # Extract headers
            message_id = email_msg.get('Message-ID', f"<{uuid.uuid4()}@somni.local>")
            in_reply_to = email_msg.get('In-Reply-To')
            references = email_msg.get('References')
            subject = email_msg.get('Subject', '(No Subject)')
            from_header = email_msg.get('From', '')
            to_header = email_msg.get('To', '')
            cc_header = email_msg.get('Cc', '')
            reply_to = email_msg.get('Reply-To', '')
            date_header = email_msg.get('Date')

            # Parse from address
            from_name, from_address = parseaddr(from_header)

            # Parse date
            received_at = email.utils.parsedate_to_datetime(date_header) if date_header else datetime.utcnow()

            # Extract body
            body_text = ""
            body_html = ""
            attachments = []

            if email_msg.is_multipart():
                for part in email_msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))

                    # Extract text
                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        body_text = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == "text/html" and "attachment" not in content_disposition:
                        body_html = part.get_payload(decode=True).decode('utf-8', errors='ignore')

                    # Extract attachments
                    if "attachment" in content_disposition:
                        filename = part.get_filename()
                        if filename:
                            attachments.append({
                                'filename': filename,
                                'mime_type': content_type,
                                'size': len(part.get_payload(decode=True))
                            })
            else:
                # Single part message
                body_text = email_msg.get_payload(decode=True).decode('utf-8', errors='ignore')

            # Create snippet (first 200 chars)
            snippet = (body_text[:200] + '...') if len(body_text) > 200 else body_text

            # Create EmailMessage object
            email_message = EmailMessage(
                email_account_id=self.account.id,
                message_id=message_id,
                in_reply_to=in_reply_to,
                references=references,
                direction='incoming',
                from_address=from_address,
                from_name=from_name,
                to_addresses=to_header,
                cc_addresses=cc_header if cc_header else None,
                reply_to=reply_to if reply_to else None,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                snippet=snippet,
                has_attachments=len(attachments) > 0,
                attachment_count=len(attachments),
                attachment_metadata=attachments if attachments else None,
                received_at=received_at,
                raw_headers=dict(email_msg.items())
            )

            # Save to database
            self.db.add(email_message)
            await self.db.commit()
            await self.db.refresh(email_message)

            return email_message

        except Exception as e:
            logger.error(f"Error parsing email: {e}")
            return None

    async def send_email(
        self,
        to_address: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        in_reply_to: Optional[str] = None,
        references: Optional[str] = None,
        attachments: Optional[List[Dict]] = None
    ) -> bool:
        """
        Send email via SMTP
        """
        try:
            # Decrypt SMTP password
            smtp_password = decrypt_value(self.account.smtp_password_encrypted)

            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = formataddr((self.account.display_name, self.account.email_address))
            msg['To'] = to_address
            msg['Subject'] = subject

            if in_reply_to:
                msg['In-Reply-To'] = in_reply_to
            if references:
                msg['References'] = references

            # Add signature if configured
            if self.account.signature:
                body_text += f"\n\n{self.account.signature}"
                if body_html:
                    body_html += f"<br><br>{self.account.signature.replace(chr(10), '<br>')}"

            # Attach text and HTML parts
            msg.attach(MIMEText(body_text, 'plain'))
            if body_html:
                msg.attach(MIMEText(body_html, 'html'))

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={attachment["filename"]}'
                    )
                    msg.attach(part)

            # Connect to SMTP
            if self.account.smtp_use_tls:
                smtp_client = smtplib.SMTP(self.account.smtp_host, self.account.smtp_port)
                smtp_client.starttls()
            else:
                smtp_client = smtplib.SMTP_SSL(self.account.smtp_host, self.account.smtp_port)

            smtp_client.login(self.account.smtp_username, smtp_password)

            # Send email
            smtp_client.send_message(msg)
            smtp_client.quit()

            # Save sent email to database
            sent_message = EmailMessage(
                email_account_id=self.account.id,
                message_id=f"<{uuid.uuid4()}@{self.account.email_address.split('@')[1]}>",
                in_reply_to=in_reply_to,
                references=references,
                direction='outgoing',
                from_address=self.account.email_address,
                from_name=self.account.display_name,
                to_addresses=to_address,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                snippet=(body_text[:200] + '...') if len(body_text) > 200 else body_text,
                received_at=datetime.utcnow(),
                ai_processed=True,
                ai_auto_replied=True
            )

            self.db.add(sent_message)
            self.account.last_email_sent = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Sent email to {to_address}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    async def forward_to_human(self, email_message: EmailMessage, note: str = ""):
        """Forward email to human agent for review"""
        if not self.account.escalation_email:
            logger.warning(f"No escalation email configured for {self.account.email_address}")
            return False

        subject = f"[AI Escalation] {email_message.subject}"
        body = f"""
This email has been escalated by the AI assistant and requires human attention.

Original From: {email_message.from_address}
Original Subject: {email_message.subject}
Received: {email_message.received_at}
AI Note: {note}

--- Original Message ---
{email_message.body_text}
"""

        return await self.send_email(
            to_address=self.account.escalation_email,
            subject=subject,
            body_text=body,
            in_reply_to=email_message.message_id
        )

    def disconnect(self):
        """Close IMAP connection"""
        if self.imap_client:
            try:
                self.imap_client.logout()
            except:
                pass
            self.imap_client = None

    async def __aenter__(self):
        await self.connect_imap()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class EmailPoller:
    """
    Background service that polls all active email accounts
    """

    def __init__(self, db_session_factory):
        self.db_session_factory = db_session_factory
        self.running = False

    async def start(self):
        """Start polling loop"""
        self.running = True
        logger.info("Email poller started")

        while self.running:
            try:
                async with self.db_session_factory() as db:
                    # Get all active email accounts
                    query = select(EmailAccount).where(EmailAccount.is_active == True)
                    result = await db.execute(query)
                    accounts = result.scalars().all()

                    for account in accounts:
                        try:
                            # Poll emails
                            service = EmailService(account, db)
                            new_messages = await service.poll_new_emails()

                            if new_messages:
                                logger.info(f"Found {len(new_messages)} new emails for {account.email_address}")

                                # Trigger AI processing (will be handled by agentic_responder)
                                from services.agentic_responder import agentic_responder
                                for msg in new_messages:
                                    asyncio.create_task(
                                        agentic_responder.process_email(msg, db)
                                    )

                            service.disconnect()

                            # Wait interval before checking next account
                            await asyncio.sleep(5)

                        except Exception as e:
                            logger.error(f"Error polling account {account.email_address}: {e}")
                            continue

                # Wait before next polling cycle
                await asyncio.sleep(60)  # Poll every minute

            except Exception as e:
                logger.error(f"Email poller error: {e}")
                await asyncio.sleep(60)

    async def stop(self):
        """Stop polling"""
        self.running = False
        logger.info("Email poller stopped")


# Singleton instance
email_poller = None


def get_email_poller(db_session_factory):
    """Get or create email poller singleton"""
    global email_poller
    if email_poller is None:
        email_poller = EmailPoller(db_session_factory)
    return email_poller


# ============================================================================
# SIMPLE STANDALONE EMAIL SENDING
# ============================================================================

async def send_email(
    to_email: str,
    subject: str,
    body: str,
    from_email: Optional[str] = None,
    from_name: Optional[str] = None,
    html_body: Optional[str] = None,
    attachments: Optional[List[Dict]] = None
) -> bool:
    """
    Simple standalone email sending function using SMTP settings from config.

    For use in background tasks and notifications that don't require
    the full EmailService with IMAP/database integration.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text email body
        from_email: Sender email (defaults to NOTIFICATIONS_FROM_EMAIL)
        from_name: Sender display name (defaults to NOTIFICATIONS_FROM_NAME)
        html_body: Optional HTML email body
        attachments: Optional list of attachments [{"filename": "...", "content": bytes}]

    Returns:
        True if email sent successfully, False otherwise
    """
    from core.config import settings

    try:
        # Use defaults from settings if not provided
        sender_email = from_email or settings.NOTIFICATIONS_FROM_EMAIL
        sender_name = from_name or settings.NOTIFICATIONS_FROM_NAME

        # Create message
        if html_body:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
        else:
            msg = MIMEText(body, 'plain')

        msg['From'] = formataddr((sender_name, sender_email))
        msg['To'] = to_email
        msg['Subject'] = subject

        # Add attachments if provided
        if attachments and isinstance(msg, MIMEMultipart):
            for attachment in attachments:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment['content'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename={attachment["filename"]}'
                )
                msg.attach(part)

        # Connect to SMTP server
        if settings.SMTP_USE_SSL:
            smtp_client = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT)
        else:
            smtp_client = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            if settings.SMTP_USE_TLS:
                smtp_client.starttls()

        # Login if credentials are configured
        if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
            smtp_client.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)

        # Send email
        smtp_client.send_message(msg)
        smtp_client.quit()

        logger.info(f"Email sent successfully to {to_email}: {subject}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"SMTP authentication failed: {e}")
        return False
    except smtplib.SMTPConnectError as e:
        logger.error(f"SMTP connection failed: {e}")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error sending email: {e}")
        return False
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False
