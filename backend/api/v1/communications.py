"""
Communications API - Manage agentic email and SMS communications
"""

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from datetime import datetime, date
import uuid

from db.database import get_db
from db.models_comms import (
    EmailAccount, EmailMessage, EmailThread,
    SMSNumber, SMSMessage, SMSConversation,
    CommunicationLog, ResponseTemplate, AgentPerformanceMetrics
)
from services.email_service import EmailService
from services.sms_service import SMSService, TwilioWebhookHandler
from services.agentic_responder import agentic_responder

router = APIRouter(prefix="/communications", tags=["communications"])


# ==========================================================================
# PYDANTIC SCHEMAS
# ==========================================================================

class EmailAccountCreate(BaseModel):
    email_address: EmailStr
    display_name: str
    account_type: str
    property_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: str
    smtp_host: str
    smtp_port: int = 587
    smtp_username: str
    smtp_password: str
    auto_reply_enabled: bool = True
    ai_agent_enabled: bool = True
    escalation_email: Optional[str] = None


class SMSNumberCreate(BaseModel):
    phone_number: str
    friendly_name: str
    number_type: str
    property_id: Optional[uuid.UUID] = None
    building_id: Optional[uuid.UUID] = None
    account_sid: str
    auth_token: str
    auto_reply_enabled: bool = True
    ai_agent_enabled: bool = True


class SendEmailRequest(BaseModel):
    email_account_id: uuid.UUID
    to_address: EmailStr
    subject: str
    body_text: str
    body_html: Optional[str] = None


class SendSMSRequest(BaseModel):
    sms_number_id: uuid.UUID
    to_number: str
    message_body: str


# ==========================================================================
# EMAIL ACCOUNT ENDPOINTS
# ==========================================================================

@router.post("/email-accounts", response_model=dict)
async def create_email_account(
    account_data: EmailAccountCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new email account for agentic responses"""
    try:
        from core.encryption import encrypt_value

        email_account = EmailAccount(
            email_address=account_data.email_address,
            display_name=account_data.display_name,
            account_type=account_data.account_type,
            property_id=account_data.property_id,
            building_id=account_data.building_id,
            imap_host=account_data.imap_host,
            imap_port=account_data.imap_port,
            imap_username=account_data.imap_username,
            imap_password_encrypted=encrypt_value(account_data.imap_password),
            smtp_host=account_data.smtp_host,
            smtp_port=account_data.smtp_port,
            smtp_username=account_data.smtp_username,
            smtp_password_encrypted=encrypt_value(account_data.smtp_password),
            auto_reply_enabled=account_data.auto_reply_enabled,
            ai_agent_enabled=account_data.ai_agent_enabled,
            escalation_email=account_data.escalation_email
        )

        db.add(email_account)
        await db.commit()
        await db.refresh(email_account)

        return {
            "id": str(email_account.id),
            "email_address": email_account.email_address,
            "is_active": email_account.is_active
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/email-accounts", response_model=List[dict])
async def list_email_accounts(
    property_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all email accounts"""
    query = select(EmailAccount)

    if property_id:
        query = query.where(EmailAccount.property_id == property_id)
    if is_active is not None:
        query = query.where(EmailAccount.is_active == is_active)

    result = await db.execute(query)
    accounts = result.scalars().all()

    return [
        {
            "id": str(acc.id),
            "email_address": acc.email_address,
            "display_name": acc.display_name,
            "account_type": acc.account_type,
            "is_active": acc.is_active,
            "total_emails_processed": acc.total_emails_processed,
            "total_auto_replies": acc.total_auto_replies,
            "last_checked": acc.last_checked.isoformat() if acc.last_checked else None
        }
        for acc in accounts
    ]


@router.get("/email-messages", response_model=List[dict])
async def list_email_messages(
    email_account_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[uuid.UUID] = None,
    ai_requires_human: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List email messages"""
    query = select(EmailMessage).order_by(desc(EmailMessage.received_at)).limit(limit)

    if email_account_id:
        query = query.where(EmailMessage.email_account_id == email_account_id)
    if tenant_id:
        query = query.where(EmailMessage.tenant_id == tenant_id)
    if ai_requires_human is not None:
        query = query.where(EmailMessage.ai_requires_human == ai_requires_human)

    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        {
            "id": str(msg.id),
            "from_address": msg.from_address,
            "subject": msg.subject,
            "snippet": msg.snippet,
            "received_at": msg.received_at.isoformat() if msg.received_at else None,
            "ai_intent": msg.ai_intent,
            "ai_confidence": float(msg.ai_confidence) if msg.ai_confidence else None,
            "ai_auto_replied": msg.ai_auto_replied,
            "ai_requires_human": msg.ai_requires_human,
            "priority": msg.priority,
            "is_read": msg.is_read
        }
        for msg in messages
    ]


@router.post("/email/send", response_model=dict)
async def send_email(
    email_data: SendEmailRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send an email manually"""
    try:
        query = select(EmailAccount).where(EmailAccount.id == email_data.email_account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()

        if not account:
            raise HTTPException(status_code=404, detail="Email account not found")

        service = EmailService(account, db)
        success = await service.send_email(
            to_address=email_data.to_address,
            subject=email_data.subject,
            body_text=email_data.body_text,
            body_html=email_data.body_html
        )

        if success:
            return {"success": True, "message": "Email sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send email")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================================
# SMS NUMBER ENDPOINTS
# ==========================================================================

@router.post("/sms-numbers", response_model=dict)
async def create_sms_number(
    sms_data: SMSNumberCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new SMS number for agentic responses"""
    try:
        from core.encryption import encrypt_value

        sms_number = SMSNumber(
            phone_number=sms_data.phone_number,
            friendly_name=sms_data.friendly_name,
            number_type=sms_data.number_type,
            property_id=sms_data.property_id,
            building_id=sms_data.building_id,
            account_sid=sms_data.account_sid,
            auth_token_encrypted=encrypt_value(sms_data.auth_token),
            auto_reply_enabled=sms_data.auto_reply_enabled,
            ai_agent_enabled=sms_data.ai_agent_enabled
        )

        db.add(sms_number)
        await db.commit()
        await db.refresh(sms_number)

        return {
            "id": str(sms_number.id),
            "phone_number": sms_number.phone_number,
            "is_active": sms_number.is_active
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sms-numbers", response_model=List[dict])
async def list_sms_numbers(
    property_id: Optional[uuid.UUID] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """List all SMS numbers"""
    query = select(SMSNumber)

    if property_id:
        query = query.where(SMSNumber.property_id == property_id)
    if is_active is not None:
        query = query.where(SMSNumber.is_active == is_active)

    result = await db.execute(query)
    numbers = result.scalars().all()

    return [
        {
            "id": str(num.id),
            "phone_number": num.phone_number,
            "friendly_name": num.friendly_name,
            "number_type": num.number_type,
            "is_active": num.is_active,
            "total_messages_received": num.total_messages_received,
            "total_auto_replies": num.total_auto_replies
        }
        for num in numbers
    ]


@router.get("/sms-messages", response_model=List[dict])
async def list_sms_messages(
    sms_number_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[uuid.UUID] = None,
    ai_requires_human: Optional[bool] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List SMS messages"""
    query = select(SMSMessage).order_by(desc(SMSMessage.received_at)).limit(limit)

    if sms_number_id:
        query = query.where(SMSMessage.sms_number_id == sms_number_id)
    if tenant_id:
        query = query.where(SMSMessage.tenant_id == tenant_id)
    if ai_requires_human is not None:
        query = query.where(SMSMessage.ai_requires_human == ai_requires_human)

    result = await db.execute(query)
    messages = result.scalars().all()

    return [
        {
            "id": str(msg.id),
            "from_number": msg.from_number,
            "message_body": msg.message_body,
            "received_at": msg.received_at.isoformat() if msg.received_at else None,
            "ai_intent": msg.ai_intent,
            "ai_confidence": float(msg.ai_confidence) if msg.ai_confidence else None,
            "ai_auto_replied": msg.ai_auto_replied,
            "ai_requires_human": msg.ai_requires_human,
            "priority": msg.priority
        }
        for msg in messages
    ]


@router.post("/sms/send", response_model=dict)
async def send_sms(
    sms_data: SendSMSRequest,
    db: AsyncSession = Depends(get_db)
):
    """Send an SMS manually"""
    try:
        query = select(SMSNumber).where(SMSNumber.id == sms_data.sms_number_id)
        result = await db.execute(query)
        sms_number = result.scalar_one_or_none()

        if not sms_number:
            raise HTTPException(status_code=404, detail="SMS number not found")

        service = SMSService(sms_number, db)
        success = await service.send_sms(
            to_number=sms_data.to_number,
            message_body=sms_data.message_body
        )

        if success:
            return {"success": True, "message": "SMS sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send SMS")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================================
# TWILIO WEBHOOKS
# ==========================================================================

@router.post("/webhooks/twilio/sms", response_model=dict)
async def twilio_sms_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Twilio SMS webhook endpoint
    Receives incoming SMS messages
    """
    try:
        form_data = await request.form()
        webhook_data = dict(form_data)

        # Process webhook
        result = await TwilioWebhookHandler.handle_incoming_sms(webhook_data, db)

        # Return TwiML response (empty for no auto-reply)
        return {"success": result.get('success', False)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks/twilio/status", response_model=dict)
async def twilio_status_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Twilio delivery status callback"""
    try:
        form_data = await request.form()
        webhook_data = dict(form_data)

        result = await TwilioWebhookHandler.handle_status_callback(webhook_data, db)
        return {"success": result.get('success', False)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================================================
# ANALYTICS & MONITORING
# ==========================================================================

@router.get("/analytics/performance", response_model=dict)
async def get_performance_metrics(
    channel: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get agent performance metrics"""
    query = select(AgentPerformanceMetrics)

    if channel:
        query = query.where(AgentPerformanceMetrics.channel == channel)
    if start_date:
        query = query.where(AgentPerformanceMetrics.metric_date >= start_date)
    if end_date:
        query = query.where(AgentPerformanceMetrics.metric_date <= end_date)

    query = query.order_by(desc(AgentPerformanceMetrics.metric_date))

    result = await db.execute(query)
    metrics = result.scalars().all()

    return {
        "metrics": [
            {
                "date": metric.metric_date.isoformat(),
                "channel": metric.channel,
                "total_received": metric.total_messages_received,
                "total_auto_replies": metric.total_auto_replies,
                "total_escalations": metric.total_human_escalations,
                "success_rate": float(metric.auto_reply_success_rate) if metric.auto_reply_success_rate else None,
                "avg_confidence": float(metric.avg_confidence_score) if metric.avg_confidence_score else None
            }
            for metric in metrics
        ]
    }


@router.get("/analytics/summary", response_model=dict)
async def get_analytics_summary(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get summary analytics for communications"""
    from datetime import timedelta

    start_date = datetime.now().date() - timedelta(days=days)

    # Email stats
    email_query = select(
        func.count(EmailMessage.id).label('total'),
        func.count(EmailMessage.id).filter(EmailMessage.ai_auto_replied == True).label('auto_replied'),
        func.count(EmailMessage.id).filter(EmailMessage.ai_requires_human == True).label('escalated'),
        func.avg(EmailMessage.ai_confidence).label('avg_confidence')
    ).where(EmailMessage.received_at >= start_date)

    email_result = await db.execute(email_query)
    email_stats = email_result.one()

    # SMS stats
    sms_query = select(
        func.count(SMSMessage.id).label('total'),
        func.count(SMSMessage.id).filter(SMSMessage.ai_auto_replied == True).label('auto_replied'),
        func.count(SMSMessage.id).filter(SMSMessage.ai_requires_human == True).label('escalated'),
        func.avg(SMSMessage.ai_confidence).label('avg_confidence')
    ).where(SMSMessage.received_at >= start_date)

    sms_result = await db.execute(sms_query)
    sms_stats = sms_result.one()

    return {
        "period_days": days,
        "email": {
            "total_received": email_stats.total or 0,
            "auto_replied": email_stats.auto_replied or 0,
            "escalated": email_stats.escalated or 0,
            "avg_confidence": float(email_stats.avg_confidence) if email_stats.avg_confidence else 0,
            "automation_rate": (email_stats.auto_replied / email_stats.total * 100) if email_stats.total else 0
        },
        "sms": {
            "total_received": sms_stats.total or 0,
            "auto_replied": sms_stats.auto_replied or 0,
            "escalated": sms_stats.escalated or 0,
            "avg_confidence": float(sms_stats.avg_confidence) if sms_stats.avg_confidence else 0,
            "automation_rate": (sms_stats.auto_replied / sms_stats.total * 100) if sms_stats.total else 0
        }
    }


@router.get("/log", response_model=List[dict])
async def get_communications_log(
    client_id: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get communications log for a client (STUB - returns empty array until models are connected)"""
    # TODO: Implement query against CommunicationLog model with client_id filter
    return []


@router.get("/communications/requiring-human", response_model=List[dict])
async def get_messages_requiring_human(
    db: AsyncSession = Depends(get_db)
):
    """Get all messages requiring human attention"""
    # This uses the view created in the schema
    query = """
    SELECT * FROM messages_for_human_review
    ORDER BY priority DESC, received_at ASC
    LIMIT 100
    """

    result = await db.execute(query)
    messages = result.mappings().all()

    return [dict(msg) for msg in messages]
