"""
Somni AI Assistant - Intelligent tenant interaction service
Integrates with Ollama LLM for natural language understanding and response generation
"""

import json
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from db.models import (
    AIConversation,
    AIMessage,
    Tenant,
    Unit,
    Lease,
    WorkOrder,
    SmartDevice
)

logger = logging.getLogger(__name__)


class SomniAIAssistant:
    """
    AI Assistant for tenant interactions
    Uses Ollama LLM with RAG (Retrieval-Augmented Generation)
    """

    def __init__(self, ollama_url: str = "http://ollama.ai.svc.cluster.local:11434"):
        self.ollama_url = ollama_url
        self.model = "llama2:13b-chat"  # Or mistral, neural-chat, etc.
        self.client = httpx.AsyncClient(timeout=30.0)

    async def chat(
        self,
        message: str,
        conversation_id: str,
        tenant_id: Optional[str],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Main chat interface - process tenant message and generate response
        """
        start_time = datetime.now()

        try:
            # 1. Get conversation context
            conversation = await self._get_conversation(conversation_id, db)
            tenant = await self._get_tenant(tenant_id, db) if tenant_id else None

            # 2. Build context from database (RAG)
            context = await self._build_context(tenant, db)

            # 3. Detect intent and extract entities
            intent_data = await self._detect_intent(message, context)

            # 4. Generate response using Ollama
            response = await self._generate_response(
                message,
                context,
                intent_data,
                conversation
            )

            # 5. Execute actions if needed
            actions = await self._execute_actions(
                intent_data,
                tenant,
                conversation_id,
                db
            )

            # 6. Save message to database
            await self._save_message(
                conversation_id=conversation_id,
                sender_type="tenant",
                message_text=message,
                intent=intent_data.get("intent"),
                confidence=intent_data.get("confidence"),
                entities=intent_data.get("entities"),
                db=db
            )

            await self._save_message(
                conversation_id=conversation_id,
                sender_type="ai",
                message_text=response["text"],
                intent=intent_data.get("intent"),
                action_taken=json.dumps(actions),
                action_result=response.get("action_results"),
                llm_model=self.model,
                tokens_used=response.get("tokens_used"),
                response_time_ms=int((datetime.now() - start_time).total_seconds() * 1000),
                db=db
            )

            await db.commit()

            return {
                "response": response["text"],
                "intent": intent_data.get("intent"),
                "confidence": intent_data.get("confidence"),
                "actions": actions,
                "suggestions": response.get("suggestions", [])
            }

        except ConnectionError as e:
            logger.error(f"AI connection error: {str(e)}")
            return {
                "response": "🔌 The AI service is currently unavailable. Please contact the property manager directly for urgent matters.",
                "error": str(e),
                "error_type": "connection_error",
                "escalate": True
            }
        except Exception as e:
            logger.error(f"Error in AI chat: {str(e)}", exc_info=True)
            return {
                "response": "I'm sorry, I'm having trouble processing your request right now. Let me connect you with a human agent.",
                "error": str(e),
                "error_type": "general_error",
                "escalate": True
            }

    async def _detect_intent(self, message: str, context: Dict) -> Dict[str, Any]:
        """
        Detect user intent using LLM
        """
        system_prompt = """
You are an intent classifier for a property management AI assistant.
Analyze the user message and classify it into one of these intents:

Intents:
- pay_rent: User wants to pay rent or asking about rent payment
- report_maintenance: User reporting a maintenance issue or problem
- ask_rent_due: User asking when rent is due
- ask_lease_info: User asking about their lease details
- book_amenity: User wants to book/reserve an amenity (gym, laundry, etc.)
- request_guest_code: User wants a guest access code for smart lock
- ask_utility: User asking about utility usage or bills
- general_question: General questions about property or policies
- emergency: Emergency situation requiring immediate attention

Extract entities:
- date: Any dates mentioned
- amount: Any dollar amounts mentioned
- location: Room, unit number, or location
- urgency: low, medium, high, critical

Respond ONLY with valid JSON:
{
    "intent": "intent_name",
    "confidence": 0.95,
    "entities": {...},
    "is_emergency": false
}
"""

        prompt = f"Context: {json.dumps(context)}\n\nUser message: {message}\n\nClassify this message:"

        try:
            response = await self._call_ollama(system_prompt, prompt)
            result = json.loads(response)
            return result
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return {"intent": "general_question", "confidence": 0.5, "entities": {}}

    async def _generate_response(
        self,
        message: str,
        context: Dict,
        intent_data: Dict,
        conversation: Optional[AIConversation]
    ) -> Dict[str, Any]:
        """
        Generate natural language response using Ollama LLM
        """
        intent = intent_data.get("intent", "general_question")

        system_prompt = f"""
You are Somni, an AI assistant for a smart building property management system.
You help tenants with rent payments, maintenance requests, amenity bookings, and general questions.

Be helpful, professional, and concise. Use a friendly tone.

Tenant context:
{json.dumps(context, indent=2)}

Current intent: {intent}
"""

        # Add conversation history
        history = ""
        if conversation:
            history = await self._get_conversation_history(conversation.id)

        prompt = f"{history}\n\nUser: {message}\n\nSomni:"

        try:
            response_text = await self._call_ollama(system_prompt, prompt)

            # Parse for action indicators
            suggestions = self._extract_suggestions(response_text, intent)

            return {
                "text": response_text,
                "suggestions": suggestions,
                "tokens_used": len(response_text.split())  # Approximate
            }
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return {
                "text": "I'm here to help! Could you please rephrase your question?",
                "tokens_used": 0
            }

    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        """
        Call Ollama API for LLM inference
        """
        try:
            response = await self.client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": f"{system_prompt}\n\n{user_prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
            )
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    async def _build_context(self, tenant: Optional[Tenant], db: AsyncSession) -> Dict:
        """
        Build context for RAG from database (tenant, lease, unit info)
        """
        context = {}

        if not tenant:
            return context

        # Get tenant info
        context["tenant"] = {
            "name": f"{tenant.first_name} {tenant.last_name}",
            "email": tenant.email,
            "phone": tenant.phone
        }

        # Get active lease
        lease_query = select(Lease).where(
            Lease.tenant_id == tenant.id,
            Lease.status == "active"
        )
        lease_result = await db.execute(lease_query)
        lease = lease_result.scalar_one_or_none()

        if lease:
            context["lease"] = {
                "start_date": lease.start_date.isoformat(),
                "end_date": lease.end_date.isoformat(),
                "monthly_rent": float(lease.monthly_rent),
                "rent_due_day": lease.rent_due_day,
                "security_deposit": float(lease.security_deposit) if lease.security_deposit else None
            }

            # Get unit info
            unit_query = select(Unit).where(Unit.id == lease.unit_id)
            unit_result = await db.execute(unit_query)
            unit = unit_result.scalar_one_or_none()

            if unit:
                context["unit"] = {
                    "unit_number": unit.unit_number,
                    "bedrooms": unit.bedrooms,
                    "bathrooms": unit.bathrooms,
                    "floor": unit.floor,
                    "square_feet": unit.square_feet
                }

                # Get smart devices for this unit
                devices_query = select(SmartDevice).where(SmartDevice.unit_id == unit.id)
                devices_result = await db.execute(devices_query)
                devices = devices_result.scalars().all()

                context["smart_devices"] = [
                    {
                        "type": d.device_type,
                        "name": d.device_name,
                        "status": d.status
                    } for d in devices
                ]

        return context

    async def _execute_actions(
        self,
        intent_data: Dict,
        tenant: Optional[Tenant],
        conversation_id: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Execute actions based on detected intent
        """
        intent = intent_data.get("intent")
        actions = []

        try:
            if intent == "pay_rent":
                # Generate payment link
                action = await self._create_payment_link(tenant, db)
                actions.append(action)

            elif intent == "report_maintenance":
                # Create work order
                action = await self._create_work_order(
                    tenant,
                    intent_data.get("entities", {}),
                    db
                )
                actions.append(action)

            elif intent == "request_guest_code":
                # Generate guest access code
                action = await self._create_guest_code(tenant, intent_data, db)
                actions.append(action)

            elif intent == "book_amenity":
                # Book amenity
                action = await self._book_amenity(tenant, intent_data, db)
                actions.append(action)

            # Save actions to database
            for action in actions:
                ai_action = AIAction(
                    conversation_id=conversation_id,
                    action_type=action["type"],
                    action_status="completed" if action.get("success") else "failed",
                    action_data=action.get("data", {}),
                    result_data=action.get("result", {}),
                    executed_at=datetime.now()
                )
                db.add(ai_action)

            await db.commit()

        except Exception as e:
            logger.error(f"Error executing actions: {e}")

        return actions

    async def _create_payment_link(self, tenant: Optional[Tenant], db: AsyncSession) -> Dict:
        """
        Generate payment link for rent
        """
        # TODO: Integrate with Invoice Ninja or payment processor
        return {
            "type": "payment_link",
            "success": True,
            "data": {"tenant_id": str(tenant.id) if tenant else None},
            "result": {
                "payment_url": "https://property.home.lan/pay/rent/abc123",
                "amount": 1250.00,
                "due_date": "2025-02-01"
            }
        }

    async def _create_work_order(
        self,
        tenant: Optional[Tenant],
        entities: Dict,
        db: AsyncSession
    ) -> Dict:
        """
        Create maintenance work order from AI chat
        """
        # TODO: Implement work order creation
        return {
            "type": "create_work_order",
            "success": True,
            "data": entities,
            "result": {
                "work_order_id": "WO-12345",
                "status": "submitted",
                "priority": entities.get("urgency", "medium")
            }
        }

    async def _create_guest_code(
        self,
        tenant: Optional[Tenant],
        intent_data: Dict,
        db: AsyncSession
    ) -> Dict:
        """
        Generate guest access code for smart lock
        """
        # TODO: Integrate with Home Assistant to create actual access code
        import random
        code = str(random.randint(1000, 9999))

        return {
            "type": "guest_access_code",
            "success": True,
            "data": intent_data.get("entities", {}),
            "result": {
                "access_code": code,
                "valid_from": "2025-01-27",
                "valid_until": "2025-01-30",
                "unit": "101"
            }
        }

    async def _book_amenity(
        self,
        tenant: Optional[Tenant],
        intent_data: Dict,
        db: AsyncSession
    ) -> Dict:
        """
        Book amenity (gym, laundry room, etc.)
        """
        # TODO: Implement amenity booking system
        return {
            "type": "book_amenity",
            "success": True,
            "data": intent_data.get("entities", {}),
            "result": {
                "amenity": "Fitness Center",
                "booking_time": "6:00 PM - 7:00 PM",
                "booking_date": "2025-01-28"
            }
        }

    async def _get_conversation(
        self,
        conversation_id: str,
        db: AsyncSession
    ) -> Optional[AIConversation]:
        """Get conversation from database"""
        query = select(AIConversation).where(AIConversation.id == conversation_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_tenant(self, tenant_id: str, db: AsyncSession) -> Optional[Tenant]:
        """Get tenant from database"""
        query = select(Tenant).where(Tenant.id == tenant_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _get_conversation_history(self, conversation_id: str) -> str:
        """Get recent conversation history for context"""
        # TODO: Implement conversation history retrieval
        return ""

    async def _save_message(
        self,
        conversation_id: str,
        sender_type: str,
        message_text: str,
        db: AsyncSession,
        **kwargs
    ):
        """Save message to database"""
        message = AIMessage(
            conversation_id=conversation_id,
            sender_type=sender_type,
            message_text=message_text,
            **kwargs
        )
        db.add(message)

    def _extract_suggestions(self, response: str, intent: str) -> List[str]:
        """Extract quick reply suggestions based on intent"""
        suggestions_map = {
            "pay_rent": ["Pay Now", "View Balance", "Payment History"],
            "report_maintenance": ["Upload Photo", "Mark as Emergency", "Check Status"],
            "ask_lease_info": ["View Lease", "Renewal Options", "Contact Manager"],
            "general_question": ["Talk to Human", "FAQs", "Contact Info"]
        }
        return suggestions_map.get(intent, ["Help", "Talk to Human"])


# Singleton instance
ai_assistant = SomniAIAssistant()
