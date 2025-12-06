"""
Agentic Responder - Orchestrates AI-powered email and SMS responses
Uses LocalAI for LLM inference and integrates with existing AI assistant
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from db.models_comms import (
    EmailMessage, SMSMessage, CommunicationLog,
    ResponseTemplate, AgentPerformanceMetrics
)
from db.models import Tenant, Unit, WorkOrder
from services.email_service import EmailService
from services.sms_service import SMSService
from services.ai_assistant import SomniAIAssistant

logger = logging.getLogger(__name__)


class AgenticResponder:
    """
    Main orchestrator for agentic email and SMS responses
    Integrates LocalAI for intent detection and response generation
    """

    def __init__(
        self,
        localai_url: str = "http://local-ai.ai.svc.cluster.local:8080",
        model: str = "gpt-3.5-turbo"  # LocalAI model name
    ):
        self.localai_url = localai_url
        self.model = model
        self.client = httpx.AsyncClient(timeout=30.0)
        self.ai_assistant = SomniAIAssistant()

    async def process_email(self, email_message: EmailMessage, db: AsyncSession):
        """
        Process incoming email with AI agent
        """
        start_time = datetime.now()

        try:
            logger.info(f"Processing email: {email_message.subject} from {email_message.from_address}")

            # 1. Identify sender (tenant, contractor, or unknown)
            sender_info = await self._identify_sender(
                email=email_message.from_address,
                db=db
            )

            if sender_info:
                email_message.tenant_id = sender_info.get('tenant_id')
                email_message.unit_id = sender_info.get('unit_id')
                email_message.contractor_id = sender_info.get('contractor_id')

            # 2. Spam detection
            is_spam = await self._detect_spam(email_message.body_text or "")
            if is_spam:
                email_message.is_spam = True
                email_message.spam_score = 0.95
                email_message.ai_processed = True
                await db.commit()
                logger.info(f"Email marked as spam: {email_message.subject}")
                return

            # 3. Intent detection and entity extraction
            intent_data = await self._detect_intent_email(email_message)

            email_message.ai_intent = intent_data.get('intent')
            email_message.ai_confidence = intent_data.get('confidence')
            email_message.ai_entities = intent_data.get('entities')
            email_message.ai_sentiment = intent_data.get('sentiment')
            email_message.message_category = intent_data.get('category')

            # 4. Determine priority
            priority = await self._determine_priority(intent_data)
            email_message.priority = priority

            # 5. Check if requires human intervention
            requires_human = await self._requires_human_review(email_message, intent_data)
            email_message.ai_requires_human = requires_human

            if requires_human:
                # Escalate to human
                await self._escalate_email(email_message, db)
                email_message.ai_processed = True
                await db.commit()
                logger.info(f"Email escalated to human: {email_message.subject}")
                return

            # 6. Build context for response generation
            context = await self._build_email_context(email_message, sender_info, db)

            # 7. Generate response
            response = await self._generate_email_response(
                email_message,
                context,
                intent_data
            )

            # 8. Execute actions (create work order, send payment link, etc.)
            actions = await self._execute_email_actions(
                email_message,
                intent_data,
                sender_info,
                db
            )

            # 9. Check confidence threshold for auto-reply
            account = email_message.account
            if (email_message.ai_confidence >= account.max_auto_reply_confidence and
                account.auto_reply_enabled and
                account.ai_agent_enabled):

                # Send automatic reply
                email_service = EmailService(account, db)
                success = await email_service.send_email(
                    to_address=email_message.from_address,
                    subject=f"Re: {email_message.subject}",
                    body_text=response['text'],
                    body_html=response.get('html'),
                    in_reply_to=email_message.message_id,
                    references=email_message.references
                )

                if success:
                    email_message.ai_auto_replied = True
                    account.total_auto_replies += 1
                    logger.info(f"Auto-replied to email: {email_message.subject}")

            # 10. Log communication
            await self._log_communication(
                channel='email',
                email_message_id=email_message.id,
                tenant_id=email_message.tenant_id,
                unit_id=email_message.unit_id,
                subject_summary=email_message.subject,
                content_snippet=email_message.snippet,
                communication_type=intent_data.get('category'),
                priority=priority,
                sentiment=intent_data.get('sentiment'),
                ai_handled=email_message.ai_auto_replied,
                ai_confidence=email_message.ai_confidence,
                human_escalation=requires_human,
                action_taken=json.dumps(actions),
                occurred_at=email_message.received_at,
                db=db
            )

            # 11. Update performance metrics
            await self._update_metrics(
                channel='email',
                intent=intent_data.get('intent'),
                auto_replied=email_message.ai_auto_replied,
                escalated=requires_human,
                response_time=(datetime.now() - start_time).total_seconds(),
                confidence=email_message.ai_confidence,
                db=db
            )

            email_message.ai_processed = True
            email_message.processed_at = datetime.now()
            await db.commit()

            logger.info(f"Email processing complete: {email_message.subject}")

        except Exception as e:
            logger.error(f"Error processing email {email_message.id}: {e}", exc_info=True)
            # Mark as requiring human review
            email_message.ai_requires_human = True
            email_message.ai_processed = True
            await db.commit()

    async def process_sms(self, sms_message: SMSMessage, db: AsyncSession):
        """
        Process incoming SMS with AI agent
        """
        start_time = datetime.now()

        try:
            logger.info(f"Processing SMS from {sms_message.from_number}: {sms_message.message_body[:50]}...")

            # 1. Identify sender
            sender_info = await self._identify_sender(
                phone=sms_message.from_number,
                db=db
            )

            if sender_info:
                sms_message.tenant_id = sender_info.get('tenant_id')
                sms_message.unit_id = sender_info.get('unit_id')
                sms_message.contractor_id = sender_info.get('contractor_id')

            # 2. Spam detection (simple keyword check for SMS)
            if any(spam_word in sms_message.message_body.lower() for spam_word in ['viagra', 'casino', 'winner']):
                sms_message.is_spam = True
                sms_message.ai_processed = True
                await db.commit()
                return

            # 3. Intent detection
            intent_data = await self._detect_intent_sms(sms_message)

            sms_message.ai_intent = intent_data.get('intent')
            sms_message.ai_confidence = intent_data.get('confidence')
            sms_message.ai_entities = intent_data.get('entities')
            sms_message.ai_sentiment = intent_data.get('sentiment')
            sms_message.message_category = intent_data.get('category')

            # 4. Determine priority
            priority = await self._determine_priority(intent_data)
            sms_message.priority = priority

            # 5. Check if requires human intervention
            requires_human = await self._requires_human_review(sms_message, intent_data)
            sms_message.ai_requires_human = requires_human

            if requires_human:
                await self._escalate_sms(sms_message, db)
                sms_message.ai_processed = True
                await db.commit()
                return

            # 6. Build context
            context = await self._build_sms_context(sms_message, sender_info, db)

            # 7. Generate response
            response = await self._generate_sms_response(
                sms_message,
                context,
                intent_data
            )

            # 8. Execute actions
            actions = await self._execute_sms_actions(
                sms_message,
                intent_data,
                sender_info,
                db
            )

            # 9. Send auto-reply if confidence is high
            sms_number = sms_message.sms_number
            if (sms_message.ai_confidence >= sms_number.max_auto_reply_confidence and
                sms_number.auto_reply_enabled and
                sms_number.ai_agent_enabled):

                sms_service = SMSService(sms_number, db)
                success = await sms_service.send_auto_reply(
                    to_number=sms_message.from_number,
                    response_text=response['text'],
                    original_message_id=sms_message.id
                )

                if success:
                    logger.info(f"Auto-replied to SMS from {sms_message.from_number}")

            # 10. Log communication
            await self._log_communication(
                channel='sms',
                sms_message_id=sms_message.id,
                tenant_id=sms_message.tenant_id,
                unit_id=sms_message.unit_id,
                content_snippet=sms_message.message_body[:200],
                communication_type=intent_data.get('category'),
                priority=priority,
                sentiment=intent_data.get('sentiment'),
                ai_handled=sms_message.ai_auto_replied,
                ai_confidence=sms_message.ai_confidence,
                human_escalation=requires_human,
                action_taken=json.dumps(actions),
                occurred_at=sms_message.received_at,
                db=db
            )

            # 11. Update metrics
            await self._update_metrics(
                channel='sms',
                intent=intent_data.get('intent'),
                auto_replied=sms_message.ai_auto_replied,
                escalated=requires_human,
                response_time=(datetime.now() - start_time).total_seconds(),
                confidence=sms_message.ai_confidence,
                db=db
            )

            sms_message.ai_processed = True
            sms_message.processed_at = datetime.now()
            await db.commit()

            logger.info(f"SMS processing complete from {sms_message.from_number}")

        except Exception as e:
            logger.error(f"Error processing SMS {sms_message.id}: {e}", exc_info=True)
            sms_message.ai_requires_human = True
            sms_message.ai_processed = True
            await db.commit()

    # ==========================================================================
    # HELPER METHODS
    # ==========================================================================

    async def _identify_sender(
        self,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        db: AsyncSession = None
    ) -> Optional[Dict]:
        """Identify sender as tenant or contractor"""
        try:
            if email:
                query = select(Tenant).where(Tenant.email == email)
                result = await db.execute(query)
                tenant = result.scalar_one_or_none()
                if tenant:
                    # Get active lease to find unit
                    from db.models import Lease
                    lease_query = select(Lease).where(
                        Lease.tenant_id == tenant.id,
                        Lease.status == 'active'
                    )
                    lease_result = await db.execute(lease_query)
                    lease = lease_result.scalar_one_or_none()

                    return {
                        'tenant_id': tenant.id,
                        'unit_id': lease.unit_id if lease else None,
                        'type': 'tenant',
                        'name': f"{tenant.first_name} {tenant.last_name}"
                    }

            if phone:
                # Normalize phone number (remove special chars)
                normalized_phone = ''.join(c for c in phone if c.isdigit())

                query = select(Tenant).where(Tenant.phone.contains(normalized_phone[-10:]))
                result = await db.execute(query)
                tenant = result.scalar_one_or_none()
                if tenant:
                    from db.models import Lease
                    lease_query = select(Lease).where(
                        Lease.tenant_id == tenant.id,
                        Lease.status == 'active'
                    )
                    lease_result = await db.execute(lease_query)
                    lease = lease_result.scalar_one_or_none()

                    return {
                        'tenant_id': tenant.id,
                        'unit_id': lease.unit_id if lease else None,
                        'type': 'tenant',
                        'name': f"{tenant.first_name} {tenant.last_name}"
                    }

            return None

        except Exception as e:
            logger.error(f"Error identifying sender: {e}")
            return None

    async def _detect_spam(self, text: str) -> bool:
        """Simple spam detection"""
        spam_keywords = [
            'viagra', 'casino', 'lottery', 'winner', 'congratulations',
            'click here now', 'limited time', 'act now', 'free money'
        ]
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in spam_keywords)

    async def _detect_intent_email(self, email_message: EmailMessage) -> Dict:
        """Detect intent from email using LocalAI"""
        prompt = f"""
Analyze this property management email and classify its intent.

From: {email_message.from_address}
Subject: {email_message.subject}
Body: {email_message.body_text[:1000]}

Classify into one of these intents:
- maintenance_request: Tenant reporting a problem
- payment_inquiry: Questions about rent or payments
- lease_question: Questions about lease terms
- amenity_booking: Booking amenities
- complaint: General complaints
- move_in_out: Move-in or move-out related
- general_inquiry: General questions
- emergency: Emergency situations

Also extract:
- sentiment: positive, neutral, negative, urgent
- category: maintenance, financial, leasing, general
- priority: low, normal, high, urgent
- entities: any specific items, dates, amounts mentioned

Respond with JSON only:
{{
  "intent": "intent_name",
  "confidence": 0.95,
  "sentiment": "neutral",
  "category": "maintenance",
  "priority": "normal",
  "entities": {{}}
}}
"""

        try:
            response = await self._call_localai(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return {
                'intent': 'general_inquiry',
                'confidence': 0.5,
                'sentiment': 'neutral',
                'category': 'general',
                'priority': 'normal'
            }

    async def _detect_intent_sms(self, sms_message: SMSMessage) -> Dict:
        """Detect intent from SMS using LocalAI"""
        prompt = f"""
Analyze this text message to a property manager.

From: {sms_message.from_number}
Message: {sms_message.message_body}

Classify intent and respond with JSON only:
{{
  "intent": "intent_name",
  "confidence": 0.95,
  "sentiment": "neutral",
  "category": "maintenance|financial|leasing|general",
  "priority": "low|normal|high|urgent",
  "entities": {{}}
}}
"""

        try:
            response = await self._call_localai(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"SMS intent detection error: {e}")
            return {
                'intent': 'general_inquiry',
                'confidence': 0.5,
                'sentiment': 'neutral',
                'category': 'general',
                'priority': 'normal'
            }

    async def _call_localai(self, prompt: str) -> str:
        """Call LocalAI API"""
        try:
            response = await self.client.post(
                f"{self.localai_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a property management assistant. Respond only with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"LocalAI API error: {e}")
            raise

    async def _generate_email_response(
        self,
        email_message: EmailMessage,
        context: Dict,
        intent_data: Dict
    ) -> Dict:
        """Generate email response using LocalAI"""
        prompt = f"""
Generate a professional email response for this property management inquiry.

Original Email:
From: {email_message.from_address}
Subject: {email_message.subject}
Body: {email_message.body_text[:1000]}

Context: {json.dumps(context, indent=2)}
Intent: {intent_data.get('intent')}

Write a helpful, professional response. Include:
- Acknowledgment of their message
- Direct answer to their question/concern
- Next steps if applicable
- Professional closing

Respond with JSON:
{{
  "text": "plain text response",
  "html": "<html>formatted response</html>"
}}
"""

        try:
            response = await self._call_localai(prompt)
            return json.loads(response)
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return {
                "text": "Thank you for your message. We've received it and will respond shortly.",
                "html": "<p>Thank you for your message. We've received it and will respond shortly.</p>"
            }

    async def _generate_sms_response(
        self,
        sms_message: SMSMessage,
        context: Dict,
        intent_data: Dict
    ) -> Dict:
        """Generate SMS response (keep it short!)"""
        prompt = f"""
Generate a brief SMS response (max 160 characters) for this property management text.

Message: {sms_message.message_body}
Context: {json.dumps(context, indent=2)}
Intent: {intent_data.get('intent')}

Keep it professional and concise.

Respond with JSON:
{{
  "text": "your sms response here"
}}
"""

        try:
            response = await self._call_localai(prompt)
            result = json.loads(response)
            # Ensure it's under 160 chars
            if len(result['text']) > 160:
                result['text'] = result['text'][:157] + "..."
            return result
        except Exception as e:
            logger.error(f"SMS response generation error: {e}")
            return {"text": "Thanks for your message. We'll respond shortly."}

    async def _build_email_context(
        self,
        email_message: EmailMessage,
        sender_info: Optional[Dict],
        db: AsyncSession
    ) -> Dict:
        """Build context for email response"""
        context = {}
        if sender_info and sender_info.get('tenant_id'):
            # Add tenant and unit info
            context['tenant_name'] = sender_info.get('name')
            if sender_info.get('unit_id'):
                unit_query = select(Unit).where(Unit.id == sender_info['unit_id'])
                unit_result = await db.execute(unit_query)
                unit = unit_result.scalar_one_or_none()
                if unit:
                    context['unit_number'] = unit.unit_number
        return context

    async def _build_sms_context(
        self,
        sms_message: SMSMessage,
        sender_info: Optional[Dict],
        db: AsyncSession
    ) -> Dict:
        """Build context for SMS response"""
        return await self._build_email_context(sms_message, sender_info, db)

    async def _execute_email_actions(
        self,
        email_message: EmailMessage,
        intent_data: Dict,
        sender_info: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Execute actions based on email intent"""
        actions = []
        intent = intent_data.get('intent')

        # Auto-create work order for maintenance requests
        if intent == 'maintenance_request' and sender_info:
            # TODO: Create work order
            actions.append({'type': 'work_order_created', 'success': True})

        return actions

    async def _execute_sms_actions(
        self,
        sms_message: SMSMessage,
        intent_data: Dict,
        sender_info: Optional[Dict],
        db: AsyncSession
    ) -> List[Dict]:
        """Execute actions based on SMS intent"""
        return await self._execute_email_actions(sms_message, intent_data, sender_info, db)

    async def _requires_human_review(self, message, intent_data: Dict) -> bool:
        """Determine if message requires human intervention"""
        # Require human review for:
        # - Low confidence
        # - Emergencies
        # - Complaints
        # - Unknown senders (no tenant/contractor match)

        if intent_data.get('confidence', 0) < 0.70:
            return True

        if intent_data.get('intent') in ['emergency', 'complaint']:
            return True

        if intent_data.get('priority') == 'urgent':
            return True

        if not message.tenant_id and not message.contractor_id:
            return True

        return False

    async def _determine_priority(self, intent_data: Dict) -> str:
        """Determine message priority"""
        return intent_data.get('priority', 'normal')

    async def _escalate_email(self, email_message: EmailMessage, db: AsyncSession):
        """Escalate email to human"""
        email_service = EmailService(email_message.account, db)
        await email_service.forward_to_human(
            email_message,
            note=f"AI confidence: {email_message.ai_confidence}, Intent: {email_message.ai_intent}"
        )
        email_message.escalated_to_human = True
        email_message.escalated_at = datetime.now()

    async def _escalate_sms(self, sms_message: SMSMessage, db: AsyncSession):
        """Escalate SMS to human"""
        sms_service = SMSService(sms_message.sms_number, db)
        await sms_service.escalate_to_human(
            sms_message,
            note=f"AI confidence: {sms_message.ai_confidence}, Intent: {sms_message.ai_intent}"
        )

    async def _log_communication(self, db: AsyncSession, **kwargs):
        """Log communication to unified log"""
        log_entry = CommunicationLog(**kwargs)
        db.add(log_entry)
        await db.commit()

    async def _update_metrics(self, db: AsyncSession, **kwargs):
        """Update daily performance metrics"""
        # TODO: Implement metrics update
        pass


# Singleton instance
agentic_responder = AgenticResponder()
