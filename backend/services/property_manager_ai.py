"""
Property Manager AI Assistant
Extends the base AI assistant with property management-specific capabilities
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from services.ai_assistant import SomniAIAssistant
from db.models import (
    Property, Client, Tenant, Unit, Building,
    Lease, WorkOrder, RentPayment, UtilityBill,
    SmartDevice
)

logger = logging.getLogger(__name__)


class PropertyManagerAI(SomniAIAssistant):
    """
    AI Assistant specialized for property managers
    Understands property management context and can help with:
    - Data analysis and insights
    - Report generation
    - Task prioritization
    - Communication drafting
    - Troubleshooting assistance
    """

    def __init__(self, ollama_url: str = "http://ollama.ai.svc.cluster.local:11434"):
        super().__init__(ollama_url)
        self.model = "llama3.1:8b"  # Faster, more capable model

    async def chat_manager(
        self,
        message: str,
        conversation_id: str,
        context: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Main chat interface for property managers
        """
        start_time = datetime.now()

        try:
            # Build comprehensive context
            manager_context = await self._build_manager_context(context, db)

            # Detect intent with property management focus
            intent_data = await self._detect_manager_intent(message, manager_context)

            # Generate response with manager context
            response = await self._generate_manager_response(
                message,
                manager_context,
                intent_data
            )

            # Execute manager-specific actions
            actions = await self._execute_manager_actions(
                intent_data,
                context,
                db
            )

            return {
                "response": response["text"],
                "intent": intent_data.get("intent"),
                "confidence": intent_data.get("confidence"),
                "actions": actions,
                "suggestions": response.get("suggestions", [])
            }

        except Exception as e:
            logger.error(f"Property Manager AI error: {str(e)}", exc_info=True)
            return {
                "response": "I encountered an issue processing your request. Could you rephrase that?",
                "error": str(e)
            }

    async def _build_manager_context(
        self,
        page_context: Dict,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for property management tasks
        """
        context = {
            "page": page_context.get("page", "unknown"),
            "user_type": page_context.get("user_type", "manager"),
            "current_date": datetime.now().isoformat()
        }

        # Get current entity context if on detail page
        entity_id = page_context.get("entity_id")
        page = page_context.get("page", "")

        if "property" in page.lower() and entity_id:
            context["property"] = await self._get_property_context(entity_id, db)
        elif "client" in page.lower() and entity_id:
            context["client"] = await self._get_client_context(entity_id, db)
        elif "tenant" in page.lower() and entity_id:
            context["tenant"] = await self._get_tenant_context(entity_id, db)

        # Get dashboard stats for insights
        context["stats"] = await self._get_dashboard_stats(db)

        # Get recent activity
        context["recent_activity"] = await self._get_recent_activity(db)

        return context

    async def _get_property_context(self, property_id: str, db: AsyncSession) -> Dict:
        """Get detailed property context"""
        query = select(Property).where(Property.id == property_id)
        result = await db.execute(query)
        property_obj = result.scalar_one_or_none()

        if not property_obj:
            return {}

        # Get buildings and units count
        buildings_query = select(func.count(Building.id)).where(Building.property_id == property_id)
        buildings_result = await db.execute(buildings_query)
        buildings_count = buildings_result.scalar()

        units_query = select(func.count(Unit.id)).join(Building).where(Building.property_id == property_id)
        units_result = await db.execute(units_query)
        units_count = units_result.scalar()

        # Get vacancy rate
        occupied_query = select(func.count(Unit.id)).join(Building).join(Lease).where(
            and_(Building.property_id == property_id, Lease.status == "active")
        )
        occupied_result = await db.execute(occupied_query)
        occupied_count = occupied_result.scalar() or 0

        vacancy_rate = ((units_count - occupied_count) / units_count * 100) if units_count > 0 else 0

        return {
            "id": str(property_obj.id),
            "name": property_obj.name,
            "address": f"{property_obj.address_line1}, {property_obj.city}, {property_obj.state}",
            "type": property_obj.property_type,
            "buildings_count": buildings_count,
            "units_count": units_count,
            "vacancy_rate": round(vacancy_rate, 1)
        }

    async def _get_client_context(self, client_id: str, db: AsyncSession) -> Dict:
        """Get client context"""
        query = select(Client).where(Client.id == client_id)
        result = await db.execute(query)
        client = result.scalar_one_or_none()

        if not client:
            return {}

        return {
            "id": str(client.id),
            "name": client.name,
            "tier": client.tier,
            "email": client.email,
            "properties_count": len(client.properties) if hasattr(client, 'properties') else 0
        }

    async def _get_tenant_context(self, tenant_id: str, db: AsyncSession) -> Dict:
        """Get tenant context"""
        query = select(Tenant).where(Tenant.id == tenant_id)
        result = await db.execute(query)
        tenant = result.scalar_one_or_none()

        if not tenant:
            return {}

        # Get active lease
        lease_query = select(Lease).where(
            and_(Lease.tenant_id == tenant_id, Lease.status == "active")
        )
        lease_result = await db.execute(lease_query)
        lease = lease_result.scalar_one_or_none()

        return {
            "id": str(tenant.id),
            "name": f"{tenant.first_name} {tenant.last_name}",
            "email": tenant.email,
            "phone": tenant.phone,
            "has_active_lease": lease is not None,
            "monthly_rent": float(lease.monthly_rent) if lease else None
        }

    async def _get_dashboard_stats(self, db: AsyncSession) -> Dict:
        """Get key dashboard statistics"""
        # Total properties
        properties_query = select(func.count(Property.id))
        properties_result = await db.execute(properties_query)
        total_properties = properties_result.scalar()

        # Total units
        units_query = select(func.count(Unit.id))
        units_result = await db.execute(units_query)
        total_units = units_result.scalar()

        # Active work orders
        open_wo_query = select(func.count(WorkOrder.id)).where(
            WorkOrder.status.in_(["pending", "in_progress"])
        )
        open_wo_result = await db.execute(open_wo_query)
        open_work_orders = open_wo_result.scalar()

        # Overdue payments (if payment model has due_date)
        # overdue_payments_query = select(func.count(Payment.id)).where(...)

        return {
            "total_properties": total_properties,
            "total_units": total_units,
            "open_work_orders": open_work_orders
        }

    async def _get_recent_activity(self, db: AsyncSession) -> Dict:
        """Get recent activity for context"""
        # Recent work orders (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_wo_query = select(func.count(WorkOrder.id)).where(
            WorkOrder.created_at >= week_ago
        )
        recent_wo_result = await db.execute(recent_wo_query)
        recent_work_orders = recent_wo_result.scalar()

        return {
            "work_orders_this_week": recent_work_orders
        }

    async def _detect_manager_intent(self, message: str, context: Dict) -> Dict[str, Any]:
        """
        Detect property manager intent
        """
        system_prompt = """
You are an intent classifier for a property management AI assistant.
Analyze the property manager's message and classify it into one of these intents:

Property Management Intents:
- analyze_data: Manager wants data analysis, insights, or comparisons
- generate_report: Manager wants to generate a report
- prioritize_tasks: Manager asking what needs attention
- troubleshoot_issue: Manager troubleshooting a problem
- draft_communication: Manager wants help writing an email/notice
- query_information: Manager asking about specific data
- smart_home_help: Manager needs help with smart devices
- financial_inquiry: Manager asking about payments, invoices, rent
- maintenance_inquiry: Manager asking about work orders or maintenance
- tenant_inquiry: Manager asking about tenants or leases

Extract entities:
- timeframe: Any time references (today, this week, last month)
- entity_type: Property, client, tenant, unit, etc.
- metric: Specific metrics mentioned (cost, occupancy, etc.)
- urgency: low, medium, high

Respond ONLY with valid JSON:
{
    "intent": "intent_name",
    "confidence": 0.95,
    "entities": {...}
}
"""

        prompt = f"Context: {json.dumps(context)}\n\nManager message: {message}\n\nClassify this message:"

        try:
            response = await self._call_ollama(system_prompt, prompt)
            # Try to extract JSON from response
            if '{' in response:
                json_start = response.index('{')
                json_end = response.rindex('}') + 1
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                return result
            else:
                logger.warning(f"No JSON in intent response: {response}")
                return {"intent": "query_information", "confidence": 0.5, "entities": {}}
        except Exception as e:
            logger.error(f"Intent detection error: {e}")
            return {"intent": "query_information", "confidence": 0.5, "entities": {}}

    async def _generate_manager_response(
        self,
        message: str,
        context: Dict,
        intent_data: Dict
    ) -> Dict[str, Any]:
        """
        Generate response tailored for property managers
        """
        intent = intent_data.get("intent", "query_information")

        system_prompt = f"""
You are Somni, an AI assistant for property managers.
You help with data analysis, insights, task prioritization, and operational questions.

Be professional, concise, and actionable. Provide specific insights when possible.

Current Context:
{json.dumps(context, indent=2)}

Current Intent: {intent}

Guidelines:
- For data queries: Provide specific numbers from context
- For analysis requests: Offer insights and comparisons
- For troubleshooting: Give step-by-step guidance
- For drafting: Provide professional templates
- Always suggest next steps
"""

        prompt = f"Property Manager: {message}\n\nSomni:"

        try:
            response_text = await self._call_ollama(system_prompt, prompt)
            suggestions = self._get_manager_suggestions(intent)

            return {
                "text": response_text,
                "suggestions": suggestions
            }
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return {
                "text": "I'm ready to help! What would you like to know?",
                "suggestions": ["Show statistics", "Recent activity", "Help"]
            }

    async def _execute_manager_actions(
        self,
        intent_data: Dict,
        context: Dict,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Execute property manager-specific actions
        """
        intent = intent_data.get("intent")
        actions = []

        try:
            if intent == "generate_report":
                action = {
                    "type": "generate_report",
                    "success": True,
                    "data": {"report_type": "performance_summary"},
                    "result": {"report_url": "/reports/latest", "format": "pdf"}
                }
                actions.append(action)

            elif intent == "analyze_data":
                action = {
                    "type": "data_analysis",
                    "success": True,
                    "data": intent_data.get("entities", {}),
                    "result": {"analysis_ready": True}
                }
                actions.append(action)

        except Exception as e:
            logger.error(f"Error executing manager actions: {e}")

        return actions

    def _get_manager_suggestions(self, intent: str) -> List[str]:
        """Get contextual suggestions for property managers"""
        suggestions_map = {
            "analyze_data": ["Show trends", "Compare properties", "Export data"],
            "generate_report": ["Download PDF", "Email report", "Schedule recurring"],
            "troubleshoot_issue": ["Show logs", "Contact support", "View documentation"],
            "draft_communication": ["Preview", "Edit draft", "Send now"],
            "query_information": ["Show details", "View history", "Related items"],
            "smart_home_help": ["Device status", "Run diagnostics", "Reset device"],
            "financial_inquiry": ["View breakdown", "Export transactions", "Generate invoice"],
            "maintenance_inquiry": ["View work orders", "Assign contractor", "Update status"],
            "prioritize_tasks": ["Show all tasks", "Mark complete", "Defer to later"]
        }
        return suggestions_map.get(intent, ["Show more", "Help", "Ask another question"])


# Singleton instance
property_manager_ai = PropertyManagerAI()
